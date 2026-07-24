import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type DbMode = "none" | "postgres" | "supabase";

export type AppSettings = {
  hostUrl: string;
  apiKey: string;
  dbMode: DbMode;
  databaseUrl: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
  nocobaseUrl: string;
  tailscaleHostname: string;
  onboarded: boolean;
};

const KEY = "texllm.settings.v1";

const DEFAULTS: AppSettings = {
  hostUrl: import.meta.env.VITE_HOST_URL || "",
  apiKey: import.meta.env.VITE_DEFAULT_API_KEY || "change-me",
  dbMode: "none",
  databaseUrl: "",
  supabaseUrl: "",
  supabaseAnonKey: "",
  nocobaseUrl: "",
  tailscaleHostname: "",
  onboarded: false,
};

type SettingsCtx = {
  settings: AppSettings;
  setSettings: (patch: Partial<AppSettings>) => void;
  resetSettings: () => void;
};

const Ctx = createContext<SettingsCtx | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setState] = useState<AppSettings>(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) return { ...DEFAULTS, ...JSON.parse(raw) };
    } catch {
      /* ignore */
    }
    return DEFAULTS;
  });

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(settings));
  }, [settings]);

  const setSettings = useCallback((patch: Partial<AppSettings>) => {
    setState((s) => ({ ...s, ...patch }));
  }, []);

  const resetSettings = useCallback(() => setState(DEFAULTS), []);

  const value = useMemo(
    () => ({ settings, setSettings, resetSettings }),
    [settings, setSettings, resetSettings]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSettings() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSettings outside provider");
  return ctx;
}
