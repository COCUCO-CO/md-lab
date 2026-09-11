export function initExportButton() {
  const exportBtn = document.querySelector('button[data-export]');
  if (!exportBtn) return;

  exportBtn.addEventListener("click", async () => {
    const confirm = window.confirm(
      "This will export the campaign report. Continue?"
    );
    if (!confirm) return;

    const systemIdEl = document.getElementById("system-id");
    const systemId = systemIdEl?.textContent?.replace("System: ", "") || "";

    // POST /api/analysis/report with {confirm: true, system_id}
    const resp = await fetch("/api/analysis/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm: true, system_id: systemId }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      const code = err.error?.code || err.detail;
      const banner = document.getElementById("error-banner");
      const cat = await fetch("/api/errors").then((r) => r.json()).catch(() => ({ errors: [] }));
      const entry = (cat.errors || []).find((e) => e.code === code);
      const text = entry
        ? `${entry.meaning} — ${entry.offer}`
        : (typeof err.detail === "string" ? err.detail : "Export failed");
      if (banner) {
        banner.hidden = false;
        banner.textContent = text;
      }
      return;
    }

    const data = await resp.json();
    const argv = data.argv || [];
    const jobId = data.job_id;

    // argv is ["--system-dir", path] two tokens
    const flag = argv.indexOf("--system-dir");
    const systemDir = flag >= 0 ? argv[flag + 1] : "";
    const id = systemDir.split("/").filter(Boolean).pop() || systemId;
    const reportPath = `systems/${id}/report/REPORT.md`;

    // Store pending report info for when job completes
    window.__pendingReport = { jobId, reportPath };
  });
}