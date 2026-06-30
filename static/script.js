// script.js
// Handles editor sync, file upload, API calls, and rendering for the
// Commentary frontend. Vanilla JS, no build step required.

(function () {
  const codeInput = document.getElementById("codeInput");
  const codeInputHighlight = document.getElementById("codeInputHighlight");
  const codeOutput = document.getElementById("codeOutput");
  const fileInput = document.getElementById("fileInput");
  const clearBtn = document.getElementById("clearBtn");
  const generateBtn = document.getElementById("generateBtn");
  const generateLabel = document.getElementById("generateLabel");
  const generateSpinner = document.getElementById("generateSpinner");
  const copyBtn = document.getElementById("copyBtn");
  const downloadBtn = document.getElementById("downloadBtn");
  const charCount = document.getElementById("charCount");
  const issuesList = document.getElementById("issuesList");
  const issueCount = document.getElementById("issueCount");
  const modelStatus = document.getElementById("modelStatus");
  const toast = document.getElementById("toast");

  let lastCommentedCode = "";
  let lintTimer = null;

  // ---------- Toast ----------

  function showToast(message, kind) {
    toast.textContent = message;
    toast.hidden = false;
    toast.className = "toast" + (kind ? ` toast--${kind}` : "");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => { toast.hidden = true; }, 4000);
  }

  // ---------- Syntax highlight sync for input editor ----------

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function refreshInputHighlight() {
    const code = codeInput.value;
    codeInputHighlight.textContent = code;
    if (window.hljs) {
      codeInputHighlight.removeAttribute("data-highlighted");
      hljs.highlightElement(codeInputHighlight);
    }
    charCount.textContent = `${code.length} character${code.length === 1 ? "" : "s"}`;
  }

  codeInput.addEventListener("input", () => {
    refreshInputHighlight();
    scheduleLint();
  });

  codeInput.addEventListener("scroll", () => {
    document.querySelector(".editor-highlight").scrollTop = codeInput.scrollTop;
    document.querySelector(".editor-highlight").scrollLeft = codeInput.scrollLeft;
  });

  // ---------- File upload ----------

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".py")) {
      showToast("Please upload a .py file.", "error");
      fileInput.value = "";
      return;
    }
    const text = await file.text();
    codeInput.value = text;
    refreshInputHighlight();
    scheduleLint();
    fileInput.value = "";
  });

  // ---------- Clear ----------

  clearBtn.addEventListener("click", () => {
    codeInput.value = "";
    refreshInputHighlight();
    renderOutput("# Your AI-commented code will appear here.");
    renderIssues([]);
    lastCommentedCode = "";
    updateOutputButtons();
  });

  // ---------- Output rendering ----------

  function renderOutput(code) {
    codeOutput.textContent = code;
    if (window.hljs) {
      codeOutput.removeAttribute("data-highlighted");
      hljs.highlightElement(codeOutput);
    }
  }

  function updateOutputButtons() {
    const hasOutput = lastCommentedCode.trim().length > 0;
    copyBtn.disabled = !hasOutput;
    downloadBtn.disabled = !hasOutput;
  }

  // ---------- Generate comments ----------

  function setGenerating(isGenerating) {
    generateBtn.disabled = isGenerating;
    generateSpinner.hidden = !isGenerating;
    generateLabel.textContent = isGenerating ? "Generating…" : "Generate Comments";
  }

  generateBtn.addEventListener("click", async () => {
    const code = codeInput.value;
    if (!code.trim()) {
      showToast("Paste some code or upload a file first.", "error");
      return;
    }

    setGenerating(true);
    try {
      const res = await fetch("/comment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || "Failed to generate comments.");
      }
      lastCommentedCode = data.commented_code;
      renderOutput(lastCommentedCode);
      updateOutputButtons();
      showToast("Comments generated.", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setGenerating(false);
    }
  });

  // ---------- Copy / Download ----------

  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(lastCommentedCode);
      showToast("Copied to clipboard.", "success");
    } catch {
      showToast("Could not copy to clipboard.", "error");
    }
  });

  downloadBtn.addEventListener("click", () => {
    const blob = new Blob([lastCommentedCode], { type: "text/x-python" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "commented_code.py";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  });

  // ---------- Lint ----------

  function scheduleLint() {
    clearTimeout(lintTimer);
    lintTimer = setTimeout(runLint, 600);
  }

  async function runLint() {
    const code = codeInput.value;
    if (!code.trim()) {
      renderIssues([]);
      return;
    }
    try {
      const res = await fetch("/lint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        renderIssues(data.issues || []);
      }
    } catch {
      // Silent failure for background linting; user can still generate comments.
    }
  }

  function renderIssues(issues) {
    issueCount.textContent = `${issues.length} issue${issues.length === 1 ? "" : "s"}`;
    if (issues.length === 0) {
      issuesList.innerHTML = `<p class="issues-empty">No issues found.</p>`;
      return;
    }
    issuesList.innerHTML = issues
      .map((issue) => {
        const badgeClass = issue.severity === "error" ? "issue-badge--error" : "issue-badge--warning";
        const loc = issue.line ? `Ln ${issue.line}${issue.column ? `:${issue.column}` : ""}` : "—";
        return `
          <div class="issue-row">
            <span class="issue-badge ${badgeClass}">${escapeHtml(issue.severity)}</span>
            <span class="issue-loc">${escapeHtml(loc)}</span>
            <span class="issue-msg">${escapeHtml(issue.message)}</span>
          </div>`;
      })
      .join("");
  }

  // ---------- Model status ----------

  async function checkModelStatus() {
    try {
      const res = await fetch("/health");
      const data = await res.json();
      const ready = data?.model?.loaded;
      const missing = !ready && data?.model?.error;
      modelStatus.textContent = ready ? "model ready" : missing ? "model unavailable" : "model not loaded yet";
      modelStatus.className = "status-pill " + (ready ? "status-pill--ready" : "status-pill--error");
    } catch {
      modelStatus.textContent = "backend unreachable";
      modelStatus.className = "status-pill status-pill--error";
    }
  }

  // ---------- Init ----------

  refreshInputHighlight();
  updateOutputButtons();
  checkModelStatus();
})();
