import { FormEvent, useState } from "react";
import { useProjects } from "../state/projects";
import {
  useTaskStore,
  type Task,
  type TaskStatus,
} from "../state/task";

export function TaskPanel() {
  const { tasks, open, setOpen, addTask, updateTask, removeTask, clearDone } =
    useTaskStore();
  const { activeProjectId, projects } = useProjects();
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [viewing, setViewing] = useState<Task | null>(null);

  function onAdd(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    addTask({
      userId: "operator",
      projectId: activeProjectId,
      title: title.trim(),
      details: details.trim(),
    });
    setTitle("");
    setDetails("");
  }

  if (!open) return null;

  return (
    <>
      <button
        type="button"
        className="task-backdrop"
        aria-label="Close tasks"
        onClick={() => setOpen(false)}
      />
      <aside className="task-panel open" aria-label="Global task checklist">
        <div className="task-panel-header">
          <h3 style={{ margin: 0 }}>Global tasks</h3>
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={() => setOpen(false)}
          >
            Close
          </button>
        </div>
        <div className="task-panel-body">
          <p className="empty-hint" style={{ marginBottom: "0.75rem" }}>
            Project:{" "}
            <strong>
              {projects.find((p) => p.id === activeProjectId)?.name ||
                activeProjectId}
            </strong>
          </p>

          <form onSubmit={onAdd} className="card" style={{ marginBottom: "0.85rem" }}>
            <div className="field">
              <label htmlFor="tp-title">Title</label>
              <input
                id="tp-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="New checklist item"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="tp-details">Details</label>
              <input
                id="tp-details"
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                placeholder="Optional notes"
              />
            </div>
            <button type="submit" className="btn btn-primary btn-sm">
              Add task
            </button>
          </form>

          <div className="btn-row" style={{ marginTop: 0, marginBottom: "0.75rem" }}>
            <button type="button" className="btn btn-sm btn-ghost" onClick={clearDone}>
              Clear done
            </button>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table className="task-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Project</th>
                  <th>Title</th>
                  <th>Status</th>
                  <th>View</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.id}>
                    <td className="mono">{t.userId}</td>
                    <td className="mono">{t.projectId.slice(0, 8)}</td>
                    <td>{t.title}</td>
                    <td>
                      <select
                        aria-label={`Status for ${t.title}`}
                        value={t.status}
                        onChange={(e) =>
                          updateTask(t.id, {
                            status: e.target.value as TaskStatus,
                          })
                        }
                      >
                        <option value="todo">todo</option>
                        <option value="in_progress">in_progress</option>
                        <option value="done">done</option>
                        <option value="blocked">blocked</option>
                      </select>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={() => setViewing(t)}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {viewing && (
            <div className="card" style={{ marginTop: "0.85rem" }}>
              <h3>{viewing.title}</h3>
              <p className="empty-hint">{viewing.details || "No details"}</p>
              <p className="mono">
                {viewing.userId} · {viewing.projectId} · {viewing.status}
              </p>
              <div className="btn-row">
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  onClick={() => setViewing(null)}
                >
                  Close
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => {
                    removeTask(viewing.id);
                    setViewing(null);
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          )}

          <div className="card" style={{ marginTop: "1rem" }}>
            <h3>Workflow automation</h3>
            <p className="empty-hint">
              When a job succeeds, mark linked tasks done (local rule). Expand
              with host webhooks later.
            </p>
            <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <input type="checkbox" defaultChecked />
              Auto-complete tasks whose title matches job goal keywords
            </label>
          </div>
        </div>
      </aside>
    </>
  );
}

/** Compact checklist embed for Jobs board */
export function TaskChecklistEmbed() {
  const { tasks, updateTask, setOpen } = useTaskStore();
  const { activeProjectId } = useProjects();
  const list = tasks.filter(
    (t) => t.projectId === activeProjectId || t.projectId === "default"
  );

  return (
    <div className="card task-embed">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "0.5rem",
        }}
      >
        <h2 style={{ margin: 0 }}>Project checklist</h2>
        <button type="button" className="btn btn-sm btn-ghost" onClick={() => setOpen(true)}>
          Open panel
        </button>
      </div>
      <ul style={{ listStyle: "none", margin: "0.75rem 0 0", padding: 0 }}>
        {list.slice(0, 8).map((t) => (
          <li
            key={t.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.35rem 0",
              borderBottom: "1px solid var(--tex-border)",
            }}
          >
            <input
              type="checkbox"
              checked={t.status === "done"}
              onChange={() =>
                updateTask(t.id, {
                  status: t.status === "done" ? "todo" : "done",
                })
              }
              aria-label={t.title}
            />
            <span
              style={{
                textDecoration: t.status === "done" ? "line-through" : "none",
                color: t.status === "done" ? "var(--tex-muted)" : undefined,
              }}
            >
              {t.title}
            </span>
            <span className="chip" style={{ marginLeft: "auto" }}>
              {t.status}
            </span>
          </li>
        ))}
        {!list.length && <p className="empty-hint">No tasks yet — open the panel to add some.</p>}
      </ul>
    </div>
  );
}
