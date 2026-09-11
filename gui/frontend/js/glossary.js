import { GLOSSARY } from "./glossary.js";

const glossaryEl = document.getElementById("glossary");
if (!glossaryEl) return;

GLOSSARY.forEach((t) => {
  const entry = document.createElement("div");
  entry.innerHTML = `<strong>${escapeHtml(t.term)}</strong> — ${escapeHtml(t.definition)}`;
  glossaryEl.appendChild(entry);
});