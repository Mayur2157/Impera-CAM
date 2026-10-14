"""Page -> words -> visual lines. Single schema for every downstream stage."""
from dataclasses import dataclass, field
from typing import List

@dataclass
class Word:
    text: str; x0: float; x1: float; top: float; bottom: float; page: int
    @property
    def mid(self): return (self.x0 + self.x1) / 2.0

@dataclass
class Line:
    words: List[Word] = field(default_factory=list)
    @property
    def top(self): return min(w.top for w in self.words)
    @property
    def bottom(self): return max(w.bottom for w in self.words)
    @property
    def page(self): return self.words[0].page
    def text(self): return " ".join(w.text for w in sorted(self.words, key=lambda w: w.x0))

def page_words(page, pageno):
    out = []
    for w in page.extract_words(use_text_flow=False, keep_blank_chars=False,
                                x_tolerance=1.5, y_tolerance=2.0):
        out.append(Word(w["text"], w["x0"], w["x1"], w["top"], w["bottom"], pageno))
    return out

def to_lines(words, y_tol=2.5):
    """Cluster words into visual lines by vertical overlap of their glyph boxes."""
    ws = sorted(words, key=lambda w: (w.top, w.x0))
    lines: list[Line] = []
    for w in ws:
        placed = False
        if lines:
            last = lines[-1]
            ov = min(w.bottom, last.bottom) - max(w.top, last.top)
            h = min(w.bottom - w.top, last.bottom - last.top) or 1
            if abs(w.top - last.top) <= y_tol or ov / h > 0.5:
                last.words.append(w); placed = True
        if not placed:
            lines.append(Line([w]))
    for ln in lines:
        ln.words.sort(key=lambda w: w.x0)
    return lines
