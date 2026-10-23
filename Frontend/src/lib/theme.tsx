import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type ThemePref = "system" | "light" | "dark";
const Ctx = createContext<{ theme: ThemePref; setTheme: (t: ThemePref) => void }>({ theme: "system", setTheme: () => {} });
const KEY = "icam.theme";

function apply(t: ThemePref) {
  const dark = t === "dark" || (t === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemePref>("system");
  useEffect(() => {
    const saved = (window.localStorage.getItem(KEY) as ThemePref | null) ?? "system";
    setThemeState(saved);
    apply(saved);
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const on = () => apply((window.localStorage.getItem(KEY) as ThemePref | null) ?? "system");
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  const setTheme = (t: ThemePref) => {
    window.localStorage.setItem(KEY, t); // UI preference only, not personal data
    setThemeState(t);
    apply(t);
  };
  return <Ctx.Provider value={{ theme, setTheme }}>{children}</Ctx.Provider>;
}

export const useTheme = () => useContext(Ctx);

/** Inline pre-hydration script to avoid a flash of the wrong theme. */
export const themeScript = `(function(){try{var t=localStorage.getItem('${KEY}')||'system';var d=t==='dark'||(t==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);if(d)document.documentElement.classList.add('dark')}catch(e){}})()`;
