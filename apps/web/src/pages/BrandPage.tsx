import { useBrand } from "../state/brand";

export function BrandPage() {
  const { brand, setBrand, resetBrand } = useBrand();

  return (
    <div>
      <h1>Brand & details</h1>
      <p className="lede">
        Customize the operator console. Tokens persist in this browser and map
        to CSS variables from the Neutral Modern design system.
      </p>

      <div className="grid-2">
        <div className="card">
          <div className="field">
            <label htmlFor="logoText">Logo / product name</label>
            <input
              id="logoText"
              value={brand.logoText}
              onChange={(e) => setBrand({ logoText: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="primary">Primary</label>
            <input
              id="primary"
              type="color"
              value={brand.primary}
              onChange={(e) => setBrand({ primary: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="accent">Accent</label>
            <input
              id="accent"
              type="color"
              value={brand.accent}
              onChange={(e) => setBrand({ accent: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="bg">Background</label>
            <input
              id="bg"
              type="color"
              value={brand.bg}
              onChange={(e) => setBrand({ bg: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="surface">Surface</label>
            <input
              id="surface"
              type="color"
              value={brand.surface}
              onChange={(e) => setBrand({ surface: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="radius">Radius ({brand.radius}px)</label>
            <input
              id="radius"
              type="range"
              min={6}
              max={24}
              value={brand.radius}
              onChange={(e) => setBrand({ radius: Number(e.target.value) })}
            />
          </div>
          <div className="field">
            <label htmlFor="density">Density ({brand.density.toFixed(2)})</label>
            <input
              id="density"
              type="range"
              min={0.85}
              max={1.2}
              step={0.05}
              value={brand.density}
              onChange={(e) => setBrand({ density: Number(e.target.value) })}
            />
          </div>
          <div className="btn-row">
            <button className="btn btn-ghost" type="button" onClick={resetBrand}>
              Reset defaults
            </button>
          </div>
        </div>

        <div className="card">
          <h2>Live preview</h2>
          <p style={{ color: "var(--tex-muted)" }}>
            Buttons, chips, and surfaces use your tokens.
          </p>
          <div className="btn-row">
            <button className="btn btn-primary" type="button">
              Primary action
            </button>
            <button className="btn btn-ghost" type="button">
              Secondary
            </button>
          </div>
          <p style={{ marginTop: "1rem" }}>
            <span className="chip ok">succeeded</span>{" "}
            <span className="chip run">running</span>{" "}
            <span className="chip warn">review</span>{" "}
            <span className="chip fail">failed</span>
          </p>
          <div
            className="card"
            style={{ marginTop: "1rem", background: "var(--tex-surface-2)" }}
          >
            <strong>{brand.logoText}</strong>
            <p style={{ margin: "0.35rem 0 0", color: "var(--tex-muted)" }}>
              Path-to-path UX · accessible motion · durable local brand
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
