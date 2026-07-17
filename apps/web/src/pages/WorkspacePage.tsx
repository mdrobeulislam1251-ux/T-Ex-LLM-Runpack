import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createTeam,
  workspaceOverview,
  type Team,
} from "../lib/workspace";
import { useSettings } from "../state/settings";

export function WorkspacePage() {
  const { settings } = useSettings();
  const [teams, setTeams] = useState<Team[]>([]);
  const [meta, setMeta] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const o = await workspaceOverview(settings);
      setTeams(o.teams || []);
      setMeta(o as unknown as Record<string, unknown>);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [settings]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    try {
      await createTeam(settings, {
        slug: slug.trim().toLowerCase().replace(/\s+/g, "-"),
        name: name.trim(),
        description: description.trim(),
        kind: "custom",
      });
      setSlug("");
      setName("");
      setDescription("");
      setShowCreate(false);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Workspace</h1>
          <p className="lede">
            Team agent dashboards and shared brains. CLI:{" "}
            <span className="mono">tex teams</span>
          </p>
        </div>
        <div className="btn-row" style={{ marginTop: 0 }}>
          <Link className="btn btn-ghost" to="/domain-review">
            Domain review
          </Link>
          <Link className="btn btn-ghost" to="/personal-bd">
            Personal BD
          </Link>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowCreate((v) => !v)}
          >
            {showCreate ? "Cancel" : "New team"}
          </button>
        </div>
      </div>

      {error && (
        <div className="status-banner error" role="alert">
          {error}
        </div>
      )}

      {meta && (
        <div className="stat-row">
          <div className="stat-card">
            <div className="label">Teams</div>
            <div className="value">{String(meta.team_count ?? 0)}</div>
          </div>
          <div className="stat-card">
            <div className="label">Brains</div>
            <div className="value">{String(meta.brain_count ?? 0)}</div>
          </div>
          <div className="stat-card">
            <div className="label">Skills</div>
            <div className="value">{String(meta.skill_count ?? 0)}</div>
          </div>
          <div className="stat-card">
            <div className="label">Ideas</div>
            <div className="value">{String(meta.idea_count ?? 0)}</div>
          </div>
        </div>
      )}

      <div className="section-title">
        <h2>Teams</h2>
        <Link to="/ideas" className="btn btn-sm btn-ghost">
          Ideas board
        </Link>
      </div>

      <div className="grid-2">
        {teams.map((t) => (
          <Link key={t.id} to={`/teams/${t.slug}`} className="team-card">
            <div className="team-card-top">
              <span
                className="team-dot"
                style={{ background: t.color || "var(--text)" }}
              />
              <div>
                <h3>{t.name}</h3>
                <div className="slug">{t.slug}</div>
              </div>
            </div>
            <p>{t.description || "No description"}</p>
          </Link>
        ))}
      </div>

      {showCreate && (
        <form className="card" style={{ marginTop: "20px" }} onSubmit={onCreate}>
          <h2>New team</h2>
          <div className="grid-2">
            <div className="field">
              <label htmlFor="ts">Slug</label>
              <input
                id="ts"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="support"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="tn">Name</label>
              <input
                id="tn"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Customer Support"
                required
              />
            </div>
          </div>
          <div className="field">
            <label htmlFor="td">Description</label>
            <input
              id="td"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Tickets, CSAT, playbooks"
            />
          </div>
          <button type="submit" className="btn btn-primary">
            Create team
          </button>
        </form>
      )}
    </div>
  );
}
