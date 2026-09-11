export function initChart(elId, traces, layout) {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  Plotly.newPlot(elId, traces, layout, { responsive: true, staticPlot: reduced });
}