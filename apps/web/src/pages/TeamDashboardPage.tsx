import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { runTeam, teamDashboard } from "../lib/workspace";
import { useSettings } from "../state/settings";

export function TeamDashboardPage() {
  const { slug = "" } = useParams();
  const { settings } = useSettings();
  const [data, setData] = useState<Awaited<ReturnType<typeof teamDashboard>> | null>(
    null
  );
  const [goal, setGoal] = useState("");
  const [runOut, setRunOut] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setData(await teamDashboard(settings, slug));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [settings, slug]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function onRun(e: FormEvent) {
    e.preventDefault();
    if (!goal.trim()) return;
    setBusy(true);
    setRunOut(null);
    try {
      const r = await runTeam(settings, slug, goal.trim());
      setRunOut(JSON.stringify(r, null, 2));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) {
    return (
      <div>
        <Link to="/workspace">← Workspace</Link>
        <div className="status-banner error">{error}</div>
      </div>
    );
  }

  if (!data) return <p className="pulse">Loading team…</p>;

  const t = data.team;

  return (
    <div>
      <p>
        <Link to="/workspace">← Workspace</Link>
      </p>
      <h1 style={{ borderLeft: `4px solid ${t.color}`, paddingLeft: "0.65rem" }}>
        {t.name}
      </h1>
      <p className="lede">
        {t.description} · agentic flow dashboard ·{" "}
        <span className="mono">tex run {t.slug} "…"</span> /{" "}
        <span className="mono">@{t.slug}</span>
      </p>

      <form className="card" onSubmit={onRun}>
        <h2>Run team flow</h2>
        <div className="field">
          <label htmlFor="goal">Goal</label>
          <textarea
            id="goal"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder={`What should ${t.name} agents deliver?`}
            required
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Running…" : "Run agentic flow"}
        </button>
      </form>

      {runOut && (
        <pre className="card mono" style={{ marginTop: "1rem", whiteSpace: "pre-wrap" }}>
          {runOut}
        </pre>
      )}

      <div className="grid-2" style={{ marginTop: "1rem" }}>
        <div className="card">
          <h2>Brains</h2>
          <ul>
            {data.brains.map((b) => (
              <li key={b.id}>
                <strong>{b.name}</strong>{" "}
                <span className="chip">{b.role}</span>
                <div className="empty-hint">{b.prompt?.slice(0, 120)}</div>
              </li>
            ))}
            {!data.brains.length && <p className="empty-hint">No brains yet</p>}
          </ul>
        </div>
        <div className="card">
          <h2>Skills</h2>
          <ul>
            {data.skills.map((s) => (
              <li key={s.id}>
                <strong>{s.name}</strong>
                <div className="empty-hint">{s.description}</div>
              </li>
            ))}
            {!data.skills.length && <p className="empty-hint">No skills yet</p>}
          </ul>
        </div>
        <div className="card">
          <h2>Flows</h2>
          {data.flows.map((f) => (
            <div key={f.id} style={{ marginBottom: "0.5rem" }}>
              <strong>{f.name}</strong>{" "}
              <span className="chip">{f.status}</span>
            </div>
          ))}
        </div>
        <div className="card">
          <h2>Activity</h2>
          <ul className="timeline">
            {data.activities.map((a, i) => (
              <li key={i}>
                <strong>{a.title}</strong>
                <div className="empty-hint">{a.detail}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
