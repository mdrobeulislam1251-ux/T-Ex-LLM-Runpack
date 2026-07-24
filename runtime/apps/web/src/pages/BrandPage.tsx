import { useBrand } from "../state/brand";
import { ThemeSwitcher } from "../components/ThemeSwitcher";

export function BrandPage() {
  const { brand, setBrand, resetBrand } = useBrand();

  return (
    <div>
      <h1>Brand base brains</h1>
      <p className="lede">
        Visual identity tokens for the console. Theme (light/sky/blue/dark)
        switches global CSS; brand colors refine the product mark.
      </p>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h2>Theme</h2>
        <ThemeSwitcher />
      </div>

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
              Reset brand defaults
            </button>
          </div>
        </div>

        <div className="card">
          <h2>Live preview</h2>
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
            <span className="chip warn">review</span>
          </p>
          <div
            className="card"
            style={{ marginTop: "1rem", background: "var(--tex-surface-2)" }}
          >
            <strong>{brand.logoText}</strong>
            <p className="empty-hint">
              Light-first · path-to-path · brand + theme layers
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
