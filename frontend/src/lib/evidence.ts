/** Scroll to an evidence card ("E3") and briefly mark it as the active source. */
export function scrollToEvidence(label: string, prefix = "") {
  const card = document.getElementById(`${prefix}evidence-${label}`);
  if (!card) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  card.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
  card.classList.add("flash");
  window.clearTimeout(Number(card.dataset.flashTimer));
  card.dataset.flashTimer = String(window.setTimeout(() => card.classList.remove("flash"), 1800));
}
