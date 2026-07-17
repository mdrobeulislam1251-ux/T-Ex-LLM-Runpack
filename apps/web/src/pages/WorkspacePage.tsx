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
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <h1>Agent workspace</h1>
      <p className="lede">
        Multi-team agentic dashboards (ops, sales, dev, tech, CEO, fulfillment,
        personal BD + custom). Same SQLite backend as{" "}
        <span className="mono">tex</span> / <span className="mono">@T-ex</span>{" "}
        CLI.
      </p>

      {error && (
        <div className="status-banner error" role="alert">
          {error}. Start host: <span className="mono">python3 -m texllm.cli serve</span>
        </div>
      )}

      {meta && (
        <div className="grid-3" style={{ marginBottom: "1rem" }}>
          <div className="card">
            <strong>{String(meta.team_count ?? 0)}</strong>
            <div className="empty-hint">Teams</div>
          </div>
          <div className="card">
            <strong>{String(meta.brain_count ?? 0)}</strong>
            <div className="empty-hint">Brains</div>
          </div>
          <div className="card">
            <strong>{String(meta.idea_count ?? 0)}</strong>
            <div className="empty-hint">Ideas</div>
          </div>
        </div>
      )}

      <h2>Team dashboards</h2>
      <div className="grid-2" style={{ marginTop: "0.75rem" }}>
        {teams.map((t) => (
          <Link
            key={t.id}
            to={`/teams/${t.slug}`}
            className="card"
            style={{
              display: "block",
              color: "inherit",
              textDecoration: "none",
              borderLeft: `4px solid ${t.color || "var(--tex-primary)"}`,
            }}
          >
            <strong>{t.name}</strong>
            <div className="mono" style={{ fontSize: "0.8rem", color: "var(--tex-muted)" }}>
              {t.slug}
            </div>
            <p className="empty-hint">{t.description}</p>
          </Link>
        ))}
      </div>

      <div className="btn-row">
        <Link className="btn btn-primary" to="/domain-review">
          Domain / website review
        </Link>
        <Link className="btn btn-ghost" to="/personal-bd">
          Personal BD agent
        </Link>
        <Link className="btn btn-ghost" to="/ideas">
          Ideas board
        </Link>
      </div>

      <form className="card" style={{ marginTop: "1.25rem" }} onSubmit={onCreate}>
        <h2>Add custom team</h2>
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

      <p className="empty-hint" style={{ marginTop: "1rem" }}>
        CLI: <span className="mono">tex teams</span> ·{" "}
        <span className="mono">tex @sales "…"</span> · Claude Code skill{" "}
        <span className="mono">skills/t-ex</span>
      </p>
    </div>
  );
}
