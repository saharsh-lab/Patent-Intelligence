// Light / dark / follow the system. Dark is the default look (no saved choice). Stored
// locally (applied before first paint by the script in layout.tsx) and in the user's
// profile (so it follows them across browsers).
export type Theme = "light" | "dark" | "system";

export function currentTheme(): Theme {
  try {
    const saved = localStorage.getItem("theme");
    return saved === "light" || saved === "system" ? saved : "dark";
  } catch {
    return "dark";
  }
}

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === "dark") delete root.dataset.theme;
  else root.dataset.theme = theme;
  try {
    if (theme === "dark") localStorage.removeItem("theme");
    else localStorage.setItem("theme", theme);
  } catch {
    // private mode: the choice lasts for this page only
  }
}
