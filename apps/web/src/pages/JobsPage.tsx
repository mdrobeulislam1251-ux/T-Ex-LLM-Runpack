import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createJob, listJobs, type Job } from "../lib/api";
import { useSettings } from "../state/settings";

function statusClass(s: string) {
  if (s === "succeeded") return "ok";
  if (s === "failed" || s === "cancelled") return "fail";
  if (s === "running" || s === "queued") return "run";
  return "";
}

export function JobsPage() {
  const { settings } = useSettings();
  const [goal, setGoal] = useState(
    "Design a durable onboarding path for our SaaS agent console"
  );
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await listJobs(settings);
      setJobs(data.jobs || []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [settings]);

  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 2500);
    return () => clearInterval(t);
  }, [refresh]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!goal.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createJob(settings, { goal: goal.trim() });
      setGoal("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Agent jobs</h1>
      <p className="lede">
        Team runners execute planner → executor → reviewer → integrator. Submit
        a goal; pin firmware in Settings later for product-specific agents.
      </p>

      {error && (
        <div className="status-banner error" role="alert">
          Host error: {error}. Start the API with{" "}
          <span className="mono">python3 -m texllm.host.app</span> or check
          Settings.
        </div>
      )}

      <form className="card" onSubmit={onSubmit} aria-label="Create job">
        <div className="field">
          <label htmlFor="goal">Goal</label>
          <textarea
            id="goal"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="What should the agent team deliver?"
            required
          />
        </div>
        <div className="btn-row">
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Dispatching…" : "Run team"}
          </button>
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => void refresh()}
          >
            Refresh
          </button>
        </div>
      </form>

      <h2 style={{ marginTop: "1.75rem" }}>Recent</h2>
      <div className="grid-2" style={{ marginTop: "0.75rem" }}>
        {jobs.length === 0 && (
          <div className="card">
            <p style={{ margin: 0, color: "var(--tex-muted)" }}>
              No jobs yet. Dispatch a goal to see the multi-agent timeline.
            </p>
          </div>
        )}
        {jobs.map((j) => (
          <Link
            key={j.id}
            to={`/jobs/${j.id}`}
            className="card"
            style={{ display: "block", color: "inherit", textDecoration: "none" }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "0.5rem",
                marginBottom: "0.5rem",
              }}
            >
              <span
                className={
                  "chip " +
                  statusClass(j.status) +
                  (j.status === "running" || j.status === "queued"
                    ? " pulse"
                    : "")
                }
              >
                {j.status}
              </span>
              <span className="mono" style={{ color: "var(--tex-muted)" }}>
                {j.firmware_id}@{j.firmware_version}
              </span>
            </div>
            <strong style={{ display: "block", marginBottom: "0.35rem" }}>
              {j.goal}
            </strong>
            {j.result?.summary && (
              <p
                style={{
                  margin: 0,
                  color: "var(--tex-muted)",
                  fontSize: "0.9rem",
                }}
              >
                {j.result.summary}
              </p>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
