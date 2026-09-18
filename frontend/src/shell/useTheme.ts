import { useEffect, useState } from "react";

export type Theme = "system" | "light" | "dark";
const STORAGE_KEY = "sinek-tema";

function readStored(): Theme {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

/** Seçilen tema <html data-theme> ile uygulanır; "system" işletim sistemi tercihini izler. */
export function useTheme(): [Theme, (theme: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(readStored);
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try {
      if (theme === "system") localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // depolama kapalıysa tema yalnızca bu oturumda geçerli
    }
  }, [theme]);
  return [theme, setTheme];
}
