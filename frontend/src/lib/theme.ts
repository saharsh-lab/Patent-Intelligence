// Light / dark / follow the system. Stored locally (applied before first paint by the
// script in layout.tsx) and in the user's profile (so it follows them across browsers).
export type Theme = "light" | "dark" | "system";

export function currentTheme(): Theme {
  try {
    const saved = localStorage.getItem("theme");
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === "system") delete root.dataset.theme;
  else root.dataset.theme = theme;
  try {
    if (theme === "system") localStorage.removeItem("theme");
    else localStorage.setItem("theme", theme);
  } catch {
    // private mode: the choice lasts for this page only
  }
}
