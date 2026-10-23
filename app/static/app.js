(() => {
  "use strict";

  // ── helpers ──────────────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);

  // Token persisted in localStorage (per-browser, cleared on sign-out).
  // Try/catch because storage can be blocked in private/sandboxed contexts.
  function getToken() {
    try { return localStorage.getItem("bsx_token"); } catch { return null; }
  }
  function setToken(t) {
    try { localStorage.setItem("bsx_token", t); } catch {}
  }
  function clearToken() {
    try { localStorage.removeItem("bsx_token"); } catch {}
  }

  // All API calls go through here so the Authorization header is always sent.
  async function api(path, opts = {}) {
    const token = getToken();
    const headers = { ...(opts.headers || {}) };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (!(opts.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    const res = await fetch(path, { ...opts, headers });
    if (res.status === 401) {
      clearToken();
      showAuth();
      throw new Error("session expired — please sign in again");
    }
    return res;
  }

  // ── panels ───────────────────────────────────────────────────────────────
  const authPanel = $("auth-panel");
  const appPanel  = $("app-panel");

  function showAuth() {
    authPanel.hidden = false;
    appPanel.hidden  = true;
  }

  function showApp(email) {
    authPanel.hidden = true;
    appPanel.hidden  = false;
    $("user-email-badge").textContent = email || "";
    loadHistory();
    probeOcr();
  }

  // ── auth tabs ─────────────────────────────────────────────────────────────
  document.querySelectorAll(".auth-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll(".auth-tab").forEach((b) =>
        b.classList.toggle("active", b.dataset.tab === tab));
      $("login-form").hidden    = tab !== "login";
      $("register-form").hidden = tab !== "register";
    });
  });

  // ── login ─────────────────────────────────────────────────────────────────
  $("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("login-error").hidden = true;
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;

    const form = new URLSearchParams();
    form.set("username", $("l-email").value);
    form.set("password", $("l-password").value);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "sign-in failed");
      setToken(data.access_token);
      const me = await (await api("/api/auth/me")).json();
      showApp(me.email);
    } catch (err) {
      const el = $("login-error");
      el.textContent = err.message;
      el.hidden = false;
    } finally {
      btn.disabled = false;
    }
  });

  // ── register ──────────────────────────────────────────────────────────────
  $("register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("register-error").hidden = true;
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;

    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: $("r-email").value,
          password: $("r-password").value,
          org_name: $("r-org").value,
          accept_terms: $("r-terms").checked,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "registration failed");
      setToken(data.access_token);
      const me = await (await api("/api/auth/me")).json();
      showApp(me.email);
    } catch (err) {
      const el = $("register-error");
      el.textContent = err.message;
      el.hidden = false;
    } finally {
      btn.disabled = false;
    }
  });

  // ── sign out ──────────────────────────────────────────────────────────────
  $("logout-btn").addEventListener("click", () => {
    clearToken();
    showAuth();
  });

  // ── file selection ────────────────────────────────────────────────────────
  const picker   = $("picker"),   dropzone = $("dropzone"), queue = $("queue");
  const form     = $("form"),     go       = $("go"),       errorBox = $("error");
  const results  = $("results"),  rowsBody = $("rows");
  let chosen = [];
  let timer  = null;

  function setFiles(list) {
    chosen = Array.from(list).filter((f) => /\.pdf$/i.test(f.name));
    queue.innerHTML = "";
    chosen.forEach((f) => {
      const li = document.createElement("li");
      const name = document.createElement("span");
      name.textContent = f.name;
      const size = document.createElement("span");
      size.textContent = (f.size / 1048576).toFixed(1) + " MB";
      li.append(name, size);
      queue.append(li);
    });
    queue.hidden = chosen.length === 0;
    go.disabled  = chosen.length === 0;
    go.textContent = chosen.length > 1
      ? `Extract ${chosen.length} statements`
      : "Extract statement";
  }

  picker.addEventListener("change", () => setFiles(picker.files));

  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); picker.click(); }
  });

  ["dragenter", "dragover"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("hot"); }));
  ["dragleave", "drop"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("hot"); }));
  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files.length) setFiles(e.dataTransfer.files);
  });

  // ── submit ────────────────────────────────────────────────────────────────
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!chosen.length) return;

    errorBox.hidden = true;
    go.disabled = true;
    go.textContent = "Working…";

    const body = new FormData();
    chosen.forEach((f) => body.append("files", f, f.name));
    body.append("password", $("password").value || "");
    body.append("bank",     $("bank").value     || "");
    body.append("use_ocr",  $("useocr").checked ? "true" : "false");
    body.append("dpi",      $("dpi").value);

    try {
      const res = await api("/api/jobs", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "upload was rejected");
      poll(data.job_id);
    } catch (err) {
      fail(err.message);
    }
  });

  function fail(msg) {
    errorBox.textContent = msg;
    errorBox.hidden = false;
    go.disabled = false;
    go.textContent = "Extract statements";
  }

  // ── polling ───────────────────────────────────────────────────────────────
  // Back off from 1 s to 3 s while nothing changes, so a hundred open tabs
  // do not hammer the API; any progress snaps back to the fast interval.
  function poll(jobId) {
    clearTimeout(timer);
    let delay = 1000, last = "";
    const tick = async () => {
      try {
        const res = await api(`/api/jobs/${jobId}`);
        if (!res.ok) throw new Error("lost track of this job");
        const job = await res.json();
        render(jobId, job);
        if (job.status === "done" || job.status === "error") {
          go.disabled = false;
          go.textContent = "Extract statements";
          loadHistory();   // refresh history after a job finishes
          return;
        }
        const state = JSON.stringify(job.files.map((f) => [f.status, f.progress, f.message]));
        delay = state === last ? Math.min(delay * 1.5, 3000) : 1000;
        last = state;
        timer = setTimeout(tick, delay);
      } catch (err) {
        fail(err.message);
      }
    };
    timer = setTimeout(tick, delay);
  }

  // ── rendering ─────────────────────────────────────────────────────────────
  function cell(row, text, cls, label) {
    const td = document.createElement("td");
    td.className = cls || "";
    if (label) td.dataset.label = label;
    if (text instanceof Node) td.append(text); else td.textContent = text;
    row.append(td);
    return td;
  }

  function render(jobId, job) {
    results.hidden = false;
    rowsBody.innerHTML = "";

    job.files.forEach((f, i) => {
      const tr = document.createElement("tr");
      cell(tr, f.name, "c-file");

      const r = f.result;
      if (f.status === "error") {
        cell(tr, "—", "c-bank");
        cell(tr, "—", "c-num", "Rows");
        const td = cell(tr, "", "c-num", "Balance check");
        td.innerHTML = '<span class="broke">failed</span>';
        cell(tr, "—", "c-num", "Needs review");
        cell(tr, f.error || "could not be read", "c-act state", "Workbook");
        rowsBody.append(tr);
        return;
      }

      if (f.status !== "done") {
        cell(tr, "—", "c-bank");
        cell(tr, "—", "c-num", "Rows");
        cell(tr, "—", "c-num", "Balance check");
        cell(tr, "—", "c-num", "Needs review");
        const td = cell(tr, "", "c-act state", "Workbook");
        const spin = document.createElement("span");
        spin.className = "spinner";
        // the message comes from the server: text, never markup
        td.append(spin, document.createTextNode(f.message || f.status));
        rowsBody.append(tr);
        return;
      }

      const pct = (r.chain * 100).toFixed(2) + "%";
      const bankCell = cell(tr, (r.info && r.info.bank) || "not printed", "c-bank");
      if (r.is_partial) {
        const badge = document.createElement("span");
        badge.className = "badge-partial";
        badge.title = r.completeness || "Partial statement excerpt";
        badge.textContent = "Partial PDF";
        bankCell.append(" ", badge);
      }
      cell(tr, String(r.rows), "c-num", "Rows");

      const chk = cell(tr, "", "c-num", "Balance check");
      const span = document.createElement("span");
      span.className = r.chain >= 0.9999 ? "tie" : "broke";
      span.textContent = pct;
      chk.append(span);

      cell(tr, String(r.flagged), "c-num", "Needs review");

      const act = cell(tr, "", "c-act", "Workbook");
      // Downloads also go through api() so the Bearer header is sent.
      // We use a click-triggered fetch and blob URL instead of a plain <a href>.
      const btn = document.createElement("button");
      btn.className = "dl link-btn";
      btn.textContent = "Download .xlsx";
      btn.addEventListener("click", async () => {
        try {
          const dlRes = await api(`/api/jobs/${jobId}/download/${i}`);
          if (!dlRes.ok) throw new Error("download failed");
          const blob = await dlRes.blob();
          const url  = URL.createObjectURL(blob);
          const a    = document.createElement("a");
          a.href     = url;
          a.download = (r.filename) || `${f.name.replace(/\.pdf$/i, "")}.xlsx`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        } catch (err) {
          alert("Download error: " + err.message);
        }
      });
      act.append(btn);

      rowsBody.append(tr);
    });
  }

  // ── job history ───────────────────────────────────────────────────────────
  async function loadHistory() {
    try {
      const res = await api("/api/jobs?limit=20");
      if (!res.ok) return;
      const jobs = await res.json();
      const tbody = $("history-rows");
      const table = $("history-table");
      const empty = $("history-empty");

      if (!jobs.length) {
        empty.hidden = false;
        table.hidden = true;
        return;
      }
      empty.hidden = true;
      table.hidden = false;
      tbody.innerHTML = "";

      jobs.forEach((job) => {
        const tr = document.createElement("tr");

        // date
        const d = new Date(job.created + "Z");
        const dateTd = document.createElement("td");
        dateTd.textContent = d.toLocaleString();
        tr.append(dateTd);

        // file count
        const cntTd = document.createElement("td");
        cntTd.textContent = job.files.length + " file" + (job.files.length !== 1 ? "s" : "");
        tr.append(cntTd);

        // status badge
        const stTd = document.createElement("td");
        const badge = document.createElement("span");
        badge.textContent = job.status;
        badge.className = "status-badge status-" + job.status;
        stTd.append(badge);
        tr.append(stTd);

        // per-file download links
        const actTd = document.createElement("td");
        job.files.forEach((f, i) => {
          if (f.status !== "done" || !f.result) return;
          const btn = document.createElement("button");
          btn.className = "dl link-btn";
          btn.textContent = f.name.replace(/\.pdf$/i, ".xlsx");
          btn.addEventListener("click", async () => {
            const dlRes = await api(`/api/jobs/${job.id}/download/${i}`);
            if (!dlRes.ok) { alert("Download failed"); return; }
            const blob = await dlRes.blob();
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement("a");
            a.href = url; a.download = f.result.filename || btn.textContent;
            document.body.appendChild(a); a.click();
            document.body.removeChild(a); URL.revokeObjectURL(url);
          });
          actTd.append(btn, " ");
        });
        tr.append(actTd);
        tbody.append(tr);
      });
    } catch { /* history is non-critical */ }
  }

  $("history-refresh").addEventListener("click", loadHistory);

  // ── OCR engine probe ──────────────────────────────────────────────────────
  function probeOcr() {
    api("/api/health").then((r) => r.json()).then((h) => {
      const el = $("engine");
      if (h.ocr_backend && h.ocr_device && String(h.ocr_device).startsWith("gpu")) {
        el.textContent = `Scanned pages will be read with ${h.ocr_backend} on `
          + h.ocr_device + (h.gpu ? ` (${h.gpu}).` : ".");
      } else if (h.ocr_backend) {
        el.textContent = `Scanned pages will be read with ${h.ocr_backend} on `
          + (h.ocr_device || "cpu") + ".";
      } else {
        el.textContent = h.ocr_warning
          || "No GPU OCR engine — scanned pages will use the PDF text layer.";
      }
      el.hidden = false;
    }).catch(() => {});
  }

  // ── startup: check for an existing token ─────────────────────────────────
  const existing = getToken();
  if (existing) {
    api("/api/auth/me")
      .then((r) => (r.ok ? r.json() : null))
      .then((me) => {
        if (me) showApp(me.email);
        else showAuth();
      })
      .catch(showAuth);
  } else {
    showAuth();
  }
})();
