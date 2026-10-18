import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listIdeas } from "../lib/workspace";
import { useSettings } from "../state/settings";

export function IdeasPage() {
  const { settings } = useSettings();
  const [ideas, setIdeas] = useState<
    { title: string; team_slug: string; summary: string; domain: string }[]
  >([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listIdeas(settings)
      .then((r) => setIdeas(r.ideas || []))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [settings]);

  return (
    <div>
      <p>
        <Link to="/workspace">← Workspace</Link>
      </p>
      <h1>Ideas board</h1>
      <p className="lede">
        From domain reviews and agents. Build brains/skills from these in team
        dashboards or CLI.
      </p>
      {error && <div className="status-banner error">{error}</div>}
      <div className="grid-2">
        {ideas.map((i, idx) => (
          <div key={idx} className="card">
            <span className="chip">{i.team_slug || "—"}</span>
            <h2 style={{ marginTop: "0.5rem" }}>{i.title}</h2>
            <p className="empty-hint">{i.summary}</p>
            {i.domain && (
              <div className="mono" style={{ fontSize: "0.8rem" }}>
                {i.domain}
              </div>
            )}
          </div>
        ))}
        {!ideas.length && !error && (
          <div className="card">
            <p className="empty-hint">
              No ideas yet. Run{" "}
              <Link to="/domain-review">Domain review</Link>.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
