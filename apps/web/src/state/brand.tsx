import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type BrandTokens = {
  logoText: string;
  primary: string;
  accent: string;
  radius: number;
  density: number;
};

const DEFAULTS: BrandTokens = {
  logoText: "T-ex LLM",
  primary: "#2563eb",
  accent: "#059669",
  radius: 12,
  density: 1,
};

const KEY = "texllm.brand.v1";

type BrandCtx = {
  brand: BrandTokens;
  setBrand: (patch: Partial<BrandTokens>) => void;
  resetBrand: () => void;
};

const Ctx = createContext<BrandCtx | null>(null);

function applyCss(b: BrandTokens) {
  const r = document.documentElement;
  // Theme owns bg/surface/text; brand owns action colors + density
  r.style.setProperty("--tex-primary", b.primary);
  r.style.setProperty("--tex-accent", b.accent);
  r.style.setProperty("--tex-radius", `${b.radius}px`);
  r.style.setProperty("--tex-density", String(b.density));
}

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brand, setBrandState] = useState<BrandTokens>(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<BrandTokens>;
        return { ...DEFAULTS, ...parsed };
      }
    } catch {
      /* ignore */
    }
    return DEFAULTS;
  });

  useEffect(() => {
    applyCss(brand);
    localStorage.setItem(KEY, JSON.stringify(brand));
  }, [brand]);

  const setBrand = useCallback((patch: Partial<BrandTokens>) => {
    setBrandState((prev) => ({ ...prev, ...patch }));
  }, []);

  const resetBrand = useCallback(() => setBrandState(DEFAULTS), []);

  const value = useMemo(
    () => ({ brand, setBrand, resetBrand }),
    [brand, setBrand, resetBrand]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useBrand() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useBrand outside provider");
  return ctx;
}
