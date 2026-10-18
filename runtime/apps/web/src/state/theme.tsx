import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ThemeId = "minimal-light" | "sky" | "blue" | "minimal-dark";

const KEY = "texllm.theme.v1";

type ThemeCtx = {
  theme: ThemeId;
  setTheme: (t: ThemeId) => void;
};

const Ctx = createContext<ThemeCtx | null>(null);

function applyTheme(theme: ThemeId) {
  document.documentElement.setAttribute("data-theme", theme);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeId>(() => {
    try {
      const raw = localStorage.getItem(KEY) as ThemeId | null;
      if (
        raw === "minimal-light" ||
        raw === "sky" ||
        raw === "blue" ||
        raw === "minimal-dark"
      ) {
        return raw;
      }
    } catch {
      /* ignore */
    }
    return "minimal-light";
  });

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(KEY, theme);
  }, [theme]);

  const setTheme = useCallback((t: ThemeId) => setThemeState(t), []);

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTheme outside ThemeProvider");
  return ctx;
}

export const THEME_OPTIONS: { id: ThemeId; label: string }[] = [
  { id: "minimal-light", label: "Minimal Light" },
  { id: "sky", label: "Sky" },
  { id: "blue", label: "Blue" },
  { id: "minimal-dark", label: "Minimal Dark" },
];
