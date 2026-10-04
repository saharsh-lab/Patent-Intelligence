/** Scroll to an evidence card ("E3") and briefly highlight it. */
export function scrollToEvidence(label: string, prefix = "") {
  const card = document.getElementById(`${prefix}evidence-${label}`);
  if (!card) return;
  card.scrollIntoView({ behavior: "smooth", block: "center" });
  card.classList.remove("flash");
  void card.offsetWidth; // restart the CSS animation
  card.classList.add("flash");
}
