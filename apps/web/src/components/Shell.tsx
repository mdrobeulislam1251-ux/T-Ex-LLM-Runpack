import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useBrand } from "../state/brand";
import { useTaskStore } from "../state/task";
import { TaskPanel } from "./TaskPanel";
import { ThemeSwitcher } from "./ThemeSwitcher";

const links = [
  { to: "/jobs", label: "Jobs" },
  { to: "/projects", label: "Projects" },
  { to: "/onboarding", label: "Onboarding" },
  { to: "/memory", label: "Memory" },
  { to: "/brains", label: "Brains" },
  { to: "/skills", label: "Skills" },
  { to: "/idea-to-agentic", label: "Idea to Agentic" },
  { to: "/chat", label: "Chat" },
  { to: "/integrations", label: "Integrations" },
  { to: "/mcp", label: "MCP" },
  { to: "/brand", label: "Brand Base Brains" },
  { to: "/settings", label: "Settings" },
  { to: "/profile", label: "User Profile" },
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
            <span>{brand.logoText}</span>
          </div>
          {links.map((l) => (
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
          <div className="nav-footer">
            <ThemeSwitcher />
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setOpen(!open)}
              aria-expanded={open}
              aria-controls="task-panel"
            >
              Tasks
              {openCount > 0 && (
                <span className="badge-count" aria-label={`${openCount} open`}>
                  {openCount}
                </span>
              )}
            </button>
            <p
              style={{
                margin: 0,
                fontSize: "0.72rem",
                color: "var(--tex-muted)",
              }}
            >
              Hyper-agentic console
            </p>
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
