export function initRunView() {
  const live = document.createElement("div");
  live.setAttribute("role", "status");
  live.setAttribute("aria-live", "polite");
  live.id = "sse-live";
  document.body.appendChild(live);

  let eventSource = null;

  function connectSSE() {
    const once = new URLSearchParams(window.location.search).has("once");
    eventSource = new EventSource(once ? "/api/events?once=true" : "/api/events");
    const onEvent = (ev) => handleEvent(ev);
    eventSource.onmessage = onEvent;
    eventSource.addEventListener("progress", onEvent);
    eventSource.addEventListener("job_state", onEvent);
    eventSource.addEventListener("job_stopped", onEvent);
    eventSource.onerror = function () {
      eventSource.close();
      eventSource = null;
      if (!once) setTimeout(connectSSE, 3000);
    };
  }

  function handleEvent(ev) {
    let payload = {};
    try { payload = JSON.parse(ev.data); } catch (_e) { return; }
    const inner = payload.data || payload;
    if (inner.percent != null) live.textContent = `${Number(inner.percent).toFixed(1)}%`;
    maybeOpenReport(inner.job_id || payload.job_id, inner.state || payload.state || ev.type);
  }

  async function maybeOpenReport(jobId, state) {
    const pending = window.__pendingReport;
    if (!pending) return;
    const done = ["finished", "failed", "cancelled", "orphaned", "job_stopped"];
    if (jobId && pending.jobId === jobId && done.includes(state)) {
      await openPendingReport();
    }
  }

  async function openPendingReport() {
    const pending = window.__pendingReport;
    if (!pending) return;
    window.__pendingReport = null;
    const path = pending.reportPath;
    const evResp = await fetch(`/api/evidence?path=${encodeURIComponent(path)}`);
    const link = document.createElement("a");
    link.href = `/api/evidence?path=${encodeURIComponent(path)}`;
    link.textContent = "Open REPORT.md";
    document.body.appendChild(link);
    if (evResp.ok) {
      const evData = await evResp.json();
      if (evData.kind === "text" && evData.text_or_url) {
        live.textContent = "Report ready";
      }
    }
  }

  async function pollJobs() {
    if (!window.__pendingReport) return;
    try {
      const r = await fetch("/api/jobs");
      if (!r.ok) return;
      const body = await r.json();
      const jobs = body.jobs || body;
      const list = Array.isArray(jobs) ? jobs : [];
      const job = list.find((j) => (j.id || j.job_id) === window.__pendingReport.jobId);
      if (job && ["finished", "failed", "cancelled", "orphaned"].includes(job.state)) {
        await openPendingReport();
      }
    } catch (_e) { /* ignore poll errors */ }
  }

  if (typeof window !== "undefined") {
    connectSSE();
    setInterval(pollJobs, 2000);
  }
}