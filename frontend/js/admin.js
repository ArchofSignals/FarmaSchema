(function () {
  const tokenInput = document.getElementById("admin-token");
  const editor = document.getElementById("schemes-editor");
  const fileInput = document.getElementById("scheme-file");
  const loginAdminBtn = document.getElementById("login-admin-btn");
  const refreshCountBtn = document.getElementById("refresh-count-btn");
  const appendFileBtn = document.getElementById("append-file-btn");
  const appendTextBtn = document.getElementById("append-text-btn");
  const statusEl = document.getElementById("admin-status");
  const countEl = document.getElementById("admin-count");

  let isAdminAuthenticated = false;

  function setAuthenticated(isAuthenticated) {
    isAdminAuthenticated = isAuthenticated;
    refreshCountBtn.disabled = !isAuthenticated;
    appendFileBtn.disabled = !isAuthenticated;
    appendTextBtn.disabled = !isAuthenticated;
  }

  function setStatus(message, type) {
    statusEl.textContent = message;
    statusEl.dataset.type = type || "";
  }

  function adminHeaders() {
    const token = tokenInput.value.trim();
    return { "X-Admin-Token": token };
  }

  function parseSchemeJson(raw) {
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (err) {
      throw new Error(`Invalid JSON: ${err.message}`);
    }

    if (!Array.isArray(parsed) && (parsed === null || typeof parsed !== "object")) {
      throw new Error("JSON must be one scheme object or an array of scheme objects.");
    }

    return parsed;
  }

  function addedCount(schemes) {
    return Array.isArray(schemes) ? schemes.length : 1;
  }

  async function refreshCount() {
    setStatus("Loading current count...", "");
    loginAdminBtn.disabled = true;
    refreshCountBtn.disabled = true;

    try {
      const data = await FarmaSchema.apiRequest("/api/admin/schemes", {
        headers: adminHeaders(),
      });
      countEl.textContent = `${data.count || 0} schemes currently in database`;
      setAuthenticated(true);
      setStatus("Admin authenticated.", "success");
    } catch (err) {
      setAuthenticated(false);
      setStatus(err.message, "error");
    } finally {
      loginAdminBtn.disabled = false;
      refreshCountBtn.disabled = !isAdminAuthenticated;
    }
  }

  async function appendSchemes(schemes, sourceLabel) {
    setStatus(`Appending ${sourceLabel}...`, "");
    appendFileBtn.disabled = true;
    appendTextBtn.disabled = true;

    try {
      const data = await FarmaSchema.apiRequest("/api/admin/schemes", {
        method: "POST",
        headers: adminHeaders(),
        body: JSON.stringify({ schemes }),
      });
      const ids = (data.added_ids || []).join(", ");
      countEl.textContent = `${data.count || 0} schemes currently in database`;
      setStatus(`Appended ${addedCount(schemes)} scheme(s). Assigned ID(s): ${ids}.`, "success");
      FarmaSchema.showToast("Scheme data appended");
    } catch (err) {
      setStatus(err.message, "error");
    } finally {
      appendFileBtn.disabled = !isAdminAuthenticated;
      appendTextBtn.disabled = !isAdminAuthenticated;
    }
  }

  async function appendFromFile() {
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      setStatus("Choose a JSON file first.", "error");
      return;
    }

    try {
      const text = await file.text();
      const schemes = parseSchemeJson(text);
      await appendSchemes(schemes, "file JSON");
      fileInput.value = "";
    } catch (err) {
      setStatus(err.message, "error");
    }
  }

  async function appendFromText() {
    const raw = editor.value.trim();
    if (!raw) {
      setStatus("Write or paste JSON first.", "error");
      return;
    }

    try {
      const schemes = parseSchemeJson(raw);
      await appendSchemes(schemes, "written JSON");
      editor.value = "";
    } catch (err) {
      setStatus(err.message, "error");
    }
  }

  loginAdminBtn.addEventListener("click", refreshCount);
  refreshCountBtn.addEventListener("click", refreshCount);
  appendFileBtn.addEventListener("click", appendFromFile);
  appendTextBtn.addEventListener("click", appendFromText);
  tokenInput.addEventListener("input", () => {
    setAuthenticated(false);
    setStatus("Authenticate again after changing the token.", "");
  });
})();
