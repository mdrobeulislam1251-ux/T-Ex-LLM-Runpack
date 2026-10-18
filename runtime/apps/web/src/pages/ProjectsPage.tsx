import { FormEvent, useState } from "react";
import { useProjects } from "../state/projects";
import { useTaskStore } from "../state/task";

export function ProjectsPage() {
  const { projects, activeProjectId, setActiveProjectId, addProject } =
    useProjects();
  const { tasks } = useTaskStore();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const p = addProject({
      name: name.trim(),
      description: description.trim(),
      status: "active",
    });
    setActiveProjectId(p.id);
    setName("");
    setDescription("");
  }

  return (
    <div>
      <h1>Projects</h1>
      <p className="lede">
        Workspaces scope tasks and future job history. Active project drives the
        global checklist.
      </p>

      <form className="card" onSubmit={onCreate}>
        <div className="field">
          <label htmlFor="pname">Name</label>
          <input
            id="pname"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="pdesc">Description</label>
          <textarea
            id="pdesc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <button type="submit" className="btn btn-primary">
          Create project
        </button>
      </form>

      <div className="grid-2" style={{ marginTop: "1rem" }}>
        {projects.map((p) => {
          const count = tasks.filter((t) => t.projectId === p.id).length;
          const active = p.id === activeProjectId;
          return (
            <div
              key={p.id}
              className="card"
              style={{
                borderColor: active ? "var(--tex-primary)" : undefined,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "0.5rem",
                }}
              >
                <h2 style={{ margin: 0 }}>{p.name}</h2>
                {active && <span className="chip ok">active</span>}
              </div>
              <p className="empty-hint">{p.description || "No description"}</p>
              <p className="mono" style={{ color: "var(--tex-muted)" }}>
                {count} tasks · {p.status}
              </p>
              <div className="btn-row">
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  disabled={active}
                  onClick={() => setActiveProjectId(p.id)}
                >
                  Set active
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
