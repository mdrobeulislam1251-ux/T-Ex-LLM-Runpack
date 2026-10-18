import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getJob, type Job } from "../lib/api";
import { useSettings } from "../state/settings";

export function JobDetailPage() {
  const { id } = useParams();
  const { settings } = useSettings();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let alive = true;
    const tick = async () => {
      try {
        const j = await getJob(settings, id);
        if (alive) {
          setJob(j);
          setError(null);
        }
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e));
      }
    };
    void tick();
    const t = setInterval(tick, 1500);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [id, settings]);

  if (error) {
    return (
      <div>
        <p>
          <Link to="/jobs">← Jobs</Link>
        </p>
        <div className="status-banner error" role="alert">
          {error}
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div>
        <p>
          <Link to="/jobs">← Jobs</Link>
        </p>
        <p className="pulse">Loading job…</p>
      </div>
    );
  }

  return (
    <div>
      <p>
        <Link to="/jobs">← Jobs</Link>
      </p>
      <h1>Job detail</h1>
      <p className="lede mono">{job.id}</p>

      <div className="grid-2">
        <div className="card">
          <h2>Status</h2>
          <p>
            <span className="chip run">{job.status}</span>{" "}
            {job.result && (
              <span
                className={
                  "chip " + (job.result.review_passed ? "ok" : "warn")
                }
              >
                review {job.result.review_passed ? "passed" : "not passed"}
              </span>
            )}
          </p>
          <p>
            <strong>Goal</strong>
            <br />
            {job.goal}
          </p>
          {job.error && (
            <p style={{ color: "var(--tex-danger)" }}>{job.error}</p>
          )}
          {job.result?.summary && (
            <p>
              <strong>Summary</strong>
              <br />
              {job.result.summary}
            </p>
          )}
          {job.result?.output && (
            <pre
              className="mono"
              style={{
                overflow: "auto",
                background: "var(--tex-bg)",
                padding: "0.75rem",
                borderRadius: 8,
              }}
            >
              {JSON.stringify(job.result.output, null, 2)}
            </pre>
          )}
        </div>

        <div className="card">
          <h2>Team handoffs</h2>
          <ol className="timeline">
            {(job.result?.handoffs || []).map((h, i) => (
              <li key={i}>
                <strong>
                  {h.from_role}
                  {h.to_role ? ` → ${h.to_role}` : ""}
                </strong>
                <div style={{ color: "var(--tex-muted)" }}>{h.content}</div>
              </li>
            ))}
            {!job.result?.handoffs?.length && (
              <li style={{ color: "var(--tex-muted)" }}>
                Waiting for roles to complete…
              </li>
            )}
          </ol>
        </div>
      </div>
    </div>
  );
}
