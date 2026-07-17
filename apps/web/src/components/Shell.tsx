import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useBrand } from "../state/brand";
import { useTaskStore } from "../state/task";
import { TaskPanel } from "./TaskPanel";
import { ThemeSwitcher } from "./ThemeSwitcher";

const sections = [
  {
    label: "Workspace",
    links: [
      { to: "/workspace", label: "Overview" },
      { to: "/domain-review", label: "Domain review" },
      { to: "/personal-bd", label: "Personal BD" },
      { to: "/ideas", label: "Ideas" },
    ],
  },
  {
    label: "Agents",
    links: [
      { to: "/jobs", label: "Jobs" },
      { to: "/chat", label: "Chat" },
      { to: "/brains", label: "Brains" },
      { to: "/skills", label: "Skills" },
    ],
  },
  {
    label: "System",
    links: [
      { to: "/settings", label: "Settings" },
      { to: "/brand", label: "Brand" },
      { to: "/profile", label: "Profile" },
      { to: "/onboarding", label: "Onboarding" },
    ],
  },
];

export function Shell() {
  const { brand } = useBrand();
  const loc = useLocation();
  const { open, setOpen, tasks } = useTaskStore();
  const openCount = tasks.filter((t) => t.status !== "done").length;

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <div className="app-shell">
        <nav className="nav-rail" aria-label="Primary">
          <div className="brand-mark">
            <span className="orb" aria-hidden />
            <span>{brand.logoText || "T-ex"}</span>
          </div>

          {sections.map((sec) => (
            <div key={sec.label} className="nav-section">
              <div className="nav-section-label">{sec.label}</div>
              {sec.links.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  className={({ isActive }) =>
                    "nav-link" + (isActive ? " active" : "")
                  }
                >
                  {l.label}
                </NavLink>
              ))}
            </div>
          ))}

          <div className="nav-footer">
            <ThemeSwitcher />
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setOpen(!open)}
              aria-expanded={open}
            >
              Tasks
              {openCount > 0 && (
                <span className="badge-count" aria-label={`${openCount} open`}>
                  {openCount}
                </span>
              )}
            </button>
          </div>
        </nav>
        <main id="main" className="main-pane page-enter" key={loc.pathname}>
          <Outlet />
        </main>
        <TaskPanel />
      </div>
    </>
  );
}
