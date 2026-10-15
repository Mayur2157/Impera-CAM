"""OCR path for scanned statements.

The only contract that matters: this module returns the *same* ``Word`` objects
the digital path returns, in PDF point coordinates. Everything downstream --
column bands, row assembly, the balance chain -- is then identical for scanned
and digital pages, which is why there is no separate scanned-document pipeline.

Default path is PaddleOCR on the GPU. Tesseract is CPU-only and is not used
unless ``BSX_OCR_DEVICE=cpu`` (or ``--backend tesseract``).

Neither engine is imported until a scanned page is actually encountered, so the
project installs and runs without them.
"""
from __future__ import annotations

import logging
import os
import re
import threading

from .layout import Word
from ..config import settings

log = logging.getLogger(__name__)

DEFAULT_DPI = 300
# Deliberately permissive. Tesseract scores ruled table headers low ('[Balance'
# comes back at 22), and dropping them costs the whole table. Junk that gets
# through is filtered later: it either fails to parse as an amount or breaks the
# balance chain, which is exactly what that check is for.
MIN_CONF = 15
_ENGINE = {"name": None, "obj": None, "device": None}
_INFER_LOCK = threading.Lock()

# auto_growth (Paddle's own default) takes GPU memory as pages need it. The
# earlier naive_best_fit pre-allocated most of the card in one chunk and, with
# Paddle 3.3 + PaddleOCR 3.7 on a 12 GB RTX 5070 Ti, ran out of memory on the
# second page of every scanned statement (measured 2026-10-15; auto_growth
# peaked at 2.5 GB). An operator who hits allocator stalls on another card can
# still set FLAGS_allocator_strategy in the environment.
os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")


class OCRUnavailable(RuntimeError):
    pass


GPU_INSTALL = (
    "GPU OCR needs the CUDA wheel, not the CPU one from PyPI:\n"
    "  pip uninstall -y paddlepaddle paddlepaddle-gpu\n"
    "  pip install paddlepaddle-gpu==3.3.0 "
    "-i https://www.paddlepaddle.org.cn/packages/stable/cu126/\n"
    "  pip install 'paddleocr>=3.0.0' Pillow"
)


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def render_page(page, dpi: int = DEFAULT_DPI):
    """pdfplumber page -> PIL image plus the points-per-pixel scale factor."""
    im = page.to_image(resolution=dpi)
    pil = im.original.convert("RGB")
    scale = 72.0 / dpi                      # pixels -> PDF points
    return pil, scale


def _preprocess(pil):
    """Greyscale + light contrast stretch. Deliberately mild: aggressive
    binarisation destroys the thin strokes in ₹ amounts and drops decimals."""
    try:
        from PIL import ImageOps
    except ImportError:
        return pil
    g = ImageOps.grayscale(pil)
    return ImageOps.autocontrast(g, cutoff=1)


# --------------------------------------------------------------------------
# device
# --------------------------------------------------------------------------
def _want_gpu() -> bool:
    return settings.ocr_device.lower() not in {"cpu", "none", "off"}


def _device_str() -> str:
    if _want_gpu():
        return f"gpu:{settings.ocr_gpu_id}"
    return "cpu"


def _paddle_cuda():
    """Return (compiled_with_cuda, gpu_name_or_none)."""
    import paddle
    compiled = bool(
        getattr(paddle.device, "is_compiled_with_cuda", lambda: False)()
        or getattr(paddle, "is_compiled_with_cuda", lambda: False)()
    )
    name = None
    if compiled:
        try:
            name = paddle.device.cuda.get_device_name(settings.ocr_gpu_id)
        except Exception:                                  # noqa: BLE001
            name = f"gpu:{settings.ocr_gpu_id}"
    return compiled, name


def _bind_paddle_gpu():
    import paddle
    compiled, name = _paddle_cuda()
    if not compiled:
        raise OCRUnavailable(
            "PaddlePaddle is a CPU build. " + GPU_INSTALL
        )
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", str(settings.ocr_gpu_id))
    paddle.device.set_device(_device_str())
    log.info("PaddleOCR device=%s (%s)", _device_str(), name or "CUDA")
    return name


# --------------------------------------------------------------------------
# engines
# --------------------------------------------------------------------------
def _make_paddle(device: str):
    from paddleocr import PaddleOCR
    attempts = [
        dict(lang="en", device=device,
             use_doc_orientation_classify=False,
             use_doc_unwarping=False,
             use_textline_orientation=False),
        dict(lang="en", device=device),
        dict(lang="en", use_gpu=device.startswith("gpu"), gpu_id=settings.ocr_gpu_id,
             use_angle_cls=False, show_log=False),
        dict(lang="en", use_angle_cls=False, show_log=False),
    ]
    last = None
    for kw in attempts:
        try:
            return PaddleOCR(**kw)
        except TypeError as e:
            last = e
    raise last or TypeError("PaddleOCR() rejected every known argument set")


def _load_engine(prefer: str | None = None):
    if _ENGINE["obj"] is not None and (prefer in (None, _ENGINE["name"])):
        return _ENGINE["name"], _ENGINE["obj"]

    prefer = (prefer or settings.ocr_backend or "paddle").lower()
    if prefer not in {"paddle", "tesseract"}:
        prefer = "paddle"

    if prefer == "tesseract":
        order = ["tesseract"]
    elif _want_gpu():
        order = ["paddle"]
    else:
        order = ["paddle", "tesseract"]

    errors = []
    for name in order:
        if name == "paddle":
            try:
                gpu_name = None
                device = _device_str()
                if _want_gpu():
                    gpu_name = _bind_paddle_gpu()
                obj = _make_paddle(device)
                _ENGINE.update(name="paddle", obj=obj, device=device)
                if gpu_name:
                    _ENGINE["gpu"] = gpu_name
                return "paddle", obj
            except Exception as e:                         # noqa: BLE001
                errors.append(f"paddleocr: {e}")
        elif name == "tesseract":
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                _ENGINE.update(name="tesseract", obj=pytesseract, device="cpu")
                return "tesseract", pytesseract
            except Exception as e:                         # noqa: BLE001
                errors.append(f"pytesseract: {e}")

    raise OCRUnavailable(
        "No GPU OCR backend available.\n" + GPU_INSTALL
        + "\nDetails: " + " | ".join(errors)
    )


# --------------------------------------------------------------------------
# paddle result adapters (2.x boxes vs 3.x rec_texts / rec_polys)
# --------------------------------------------------------------------------
def _get(obj, key):
    if obj is None:
        return None
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        res = obj.get("res")
        if isinstance(res, dict) and key in res:
            return res[key]
        return None
    if hasattr(obj, key):
        return getattr(obj, key)
    try:
        return obj[key]
    except Exception:                                      # noqa: BLE001
        return None


def _box_xy(box):
    if box is None:
        return None, None
    if hasattr(box, "tolist"):
        box = box.tolist()
    if isinstance(box, (list, tuple)) and box and isinstance(box[0], (int, float)):
        # [x0, y0, x1, y1]
        if len(box) >= 4:
            xs, ys = [box[0], box[2]], [box[1], box[3]]
            return xs, ys
        return None, None
    xs, ys = [], []
    for p in box:
        if hasattr(p, "tolist"):
            p = p.tolist()
        xs.append(float(p[0]))
        ys.append(float(p[1]))
    return xs, ys


def _iter_paddle_dets(res):
    """Yield (text, xs, ys) from either PaddleOCR 2.x or 3.x output."""
    if not res:
        return
    pages = res if isinstance(res, list) else [res]
    for page in pages:
        if not page:
            continue
        texts = _get(page, "rec_texts")
        polys = _get(page, "rec_polys") or _get(page, "dt_polys")
        if texts is None and hasattr(page, "json"):
            data = page.json
            if callable(data):
                try:
                    data = data()
                except TypeError:
                    data = None
            texts = _get(data, "rec_texts")
            polys = _get(data, "rec_polys") or _get(data, "dt_polys")
        if texts is not None and polys is not None:
            for text, box in zip(texts, polys):
                xs, ys = _box_xy(box)
                if xs:
                    yield text, xs, ys
            continue
        # 2.x: a page is [[box, (text, conf)], ...]
        dets = page
        if isinstance(page, list) and page and isinstance(page[0], list) \
                and page[0] and not isinstance(page[0][0], (int, float)):
            # extra page wrapper: [ [det, det], ... ]
            for inner in page:
                if not inner:
                    continue
                if isinstance(inner, list) and inner and isinstance(inner[0], list):
                    dets = inner
                    break
        if not isinstance(dets, list):
            continue
        for det in dets:
            if not det or len(det) < 2:
                continue
            box, payload = det[0], det[1]
            text = payload[0] if isinstance(payload, (list, tuple)) else payload
            xs, ys = _box_xy(box)
            if xs:
                yield text, xs, ys


def _run_paddle(engine, arr):
    with _INFER_LOCK:
        if hasattr(engine, "predict"):
            try:
                return engine.predict(arr)
            except TypeError:
                try:
                    return engine.predict(input=arr)
                except TypeError:
                    pass
        try:
            return engine.ocr(arr, cls=False)
        except TypeError:
            return engine.ocr(arr)


def _paddle_words(engine, pil, scale, pageno):
    import numpy as np
    # PaddleOCR 3.x detection takes HxWx3 only; the greyscale from _preprocess
    # becomes three identical channels, so the contrast stretch is kept
    if pil.mode != "RGB":
        pil = pil.convert("RGB")
    res = _run_paddle(engine, np.array(pil))
    out = []
    for text, xs, ys in _iter_paddle_dets(res):
        text = " ".join(filter(None, (clean_token(t) for t in str(text).split())))
        if not text:
            continue
        out.extend(_split_tokens(text, min(xs), max(xs), min(ys), max(ys),
                                 scale, pageno))
    return out


def _tesseract_words(engine, pil, scale, pageno):
    data = engine.image_to_data(pil, output_type=engine.Output.DICT,
                                config="--psm 6")
    out = []
    for i, raw in enumerate(data["text"]):
        text = clean_token(raw or "")
        if not text:
            continue
        try:
            if float(data.get("conf", [0])[i] or 0) < MIN_CONF:
                continue
        except (TypeError, ValueError):
            pass
        x, y = data["left"][i], data["top"][i]
        w, h = data["width"][i], data["height"][i]
        out.append(Word(text.strip(), x * scale, (x + w) * scale,
                        y * scale, (y + h) * scale, pageno))
    return out


# OCR reads a table's ruling lines as characters and welds them onto the
# neighbouring word: '|Withdrawals', '[Balance', '=----_|Instr'. Left alone
# these break header matching and turn amounts into junk, so every token is
# stripped of rule glyphs at its edges and dropped if that is all it was.
_RULE_CHARS = "|[]{}_=~-\u2014\u2013\u2500\u2502 \t"
_ONLY_RULES = re.compile(r"^[|\[\]{}_=~\-\u2014\u2013\u2500\u2502.,;:'\"`]+$")


def clean_token(t: str) -> str:
    t = t.strip().strip(_RULE_CHARS)
    if not t or _ONLY_RULES.match(t):
        return ""
    # a leading rule fused to a word: '|Withdrawals' -> 'Withdrawals'
    t = re.sub(r"^[|\[\]_=~]+", "", t)
    t = re.sub(r"[|\[\]_=~]+$", "", t)
    return t.strip()


def _split_tokens(text, x0, x1, top, bottom, scale, pageno):
    """Paddle returns whole lines. Column banding needs per-token boxes, so a
    line is split on spaces and its width apportioned by character count. This
    is an approximation, but amounts and dates are single tokens, which is what
    the band assignment actually depends on."""
    parts = text.split()
    if len(parts) <= 1:
        return [Word(text.strip(), x0 * scale, x1 * scale,
                     top * scale, bottom * scale, pageno)]
    total = sum(len(p) for p in parts) + len(parts) - 1
    span = x1 - x0
    words, cursor = [], x0
    for p in parts:
        w = span * (len(p) / total)
        words.append(Word(p, cursor * scale, (cursor + w) * scale,
                          top * scale, bottom * scale, pageno))
        cursor += w + span * (1 / total)
    return words


# --------------------------------------------------------------------------
# public
# --------------------------------------------------------------------------
def ocr_page_words(page, pageno: int, dpi: int = DEFAULT_DPI,
                   backend: str | None = None):
    """Scanned page -> list[Word] in PDF point coordinates."""
    name, engine = _load_engine(backend)
    pil, scale = render_page(page, dpi)
    pil = _preprocess(pil)
    if name == "paddle":
        return _paddle_words(engine, pil, scale, pageno)
    return _tesseract_words(engine, pil, scale, pageno)


def probe() -> dict:
    """Cheap GPU / backend check. Does not construct the OCR model."""
    info = {
        "backend": None,
        "device": None,
        "cuda_compiled": False,
        "gpu": None,
        "warning": None,
    }
    try:
        compiled, name = _paddle_cuda()
        info["cuda_compiled"] = compiled
        info["gpu"] = name
    except Exception:                                      # noqa: BLE001
        pass

    paddleocr_ok = False
    try:
        import paddleocr  # noqa: F401
        paddleocr_ok = True
    except Exception:                                      # noqa: BLE001
        paddleocr_ok = False

    if _want_gpu():
        if paddleocr_ok and info["cuda_compiled"]:
            info["backend"] = "paddle"
            info["device"] = _device_str()
        elif paddleocr_ok and not info["cuda_compiled"]:
            info["warning"] = "paddlepaddle is CPU-only; install paddlepaddle-gpu"
        elif not paddleocr_ok:
            info["warning"] = "PaddleOCR is not installed"
        if not info["cuda_compiled"] and info["warning"] is None:
            info["warning"] = "CUDA not available to PaddlePaddle"
    else:
        if paddleocr_ok:
            info["backend"] = "paddle"
            info["device"] = "cpu" if not info["cuda_compiled"] else _device_str()
        else:
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                info["backend"] = "tesseract"
                info["device"] = "cpu"
            except Exception:                              # noqa: BLE001
                info["warning"] = "No OCR engine installed"
    return info


def available() -> str | None:
    return probe()["backend"]
