import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { runPersonalBd } from "../lib/workspace";
import { useSettings } from "../state/settings";

export function PersonalBdPage() {
  const { settings } = useSettings();
  const [goal, setGoal] = useState(
    "Map 5 growth experiments for our agent platform this quarter"
  );
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await runPersonalBd(settings, goal.trim());
      setOut(JSON.stringify(r, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <p>
        <Link to="/workspace">← Workspace</Link>
      </p>
      <h1>Personal business development</h1>
      <p className="lede">
        Your personal BD agent on the <strong>same database</strong> as company
        teams. CLI: <span className="mono">tex bd "…"</span>
      </p>

      <form className="card" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="bd">Goal</label>
          <textarea
            id="bd"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            required
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Working…" : "Run personal BD agent"}
        </button>
      </form>

      {error && (
        <div className="status-banner error" style={{ marginTop: "1rem" }}>
          {error}
        </div>
      )}
      {out && (
        <pre className="card mono" style={{ marginTop: "1rem", whiteSpace: "pre-wrap" }}>
          {out}
        </pre>
      )}
    </div>
  );
}
