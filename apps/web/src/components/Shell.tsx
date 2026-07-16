import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useBrand } from "../state/brand";

const links = [
  { to: "/jobs", label: "Jobs", end: false },
  { to: "/onboarding", label: "Onboarding", end: false },
  { to: "/brand", label: "Brand", end: true },
  { to: "/settings", label: "Settings", end: true },
];

export function Shell() {
  const { brand } = useBrand();
  const loc = useLocation();

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <div className="app-shell">
        <nav className="nav-rail" aria-label="Primary">
          <div className="brand-mark">
            <span className="orb" aria-hidden />
            <span>{brand.logoText}</span>
          </div>
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                "nav-link" + (isActive ? " active" : "")
              }
            >
              {l.label}
            </NavLink>
          ))}
          <p
            style={{
              marginTop: "auto",
              padding: "1rem 0.5rem 0",
              fontSize: "0.75rem",
              color: "var(--tex-muted)",
            }}
          >
            Hyper-agentic console · team runners
          </p>
        </nav>
        <main id="main" className="main-pane page-enter" key={loc.pathname}>
          <Outlet />
        </main>
      </div>
    </>
  );
}
