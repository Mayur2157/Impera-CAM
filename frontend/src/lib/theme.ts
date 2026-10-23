export type Theme = "light" | "dark";
const KEY = "icam.theme";

export function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

/** Switch theme and remember the choice for this browser (a convenience only). */
export function setTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    /* storage blocked: the choice lasts for this page only */
  }
}
