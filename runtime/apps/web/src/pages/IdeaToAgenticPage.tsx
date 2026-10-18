import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { createJob } from "../lib/api";
import { useSettings } from "../state/settings";
import { useTaskStore } from "../state/task";
import { useProjects } from "../state/projects";

export function IdeaToAgenticPage() {
  const { settings } = useSettings();
  const { addTask } = useTaskStore();
  const { activeProjectId } = useProjects();
  const [idea, setIdea] = useState("");
  const [plan, setPlan] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!idea.trim()) return;
    setBusy(true);
    setError(null);
    setPlan(null);
    try {
      addTask({
        userId: "operator",
        projectId: activeProjectId,
        title: `Idea: ${idea.trim().slice(0, 48)}`,
        details: idea.trim(),
        status: "in_progress",
      });
      const job = await createJob(settings, {
        goal: `Turn this product idea into an agentic plan with roles, tools, firmware name, and MVP milestones:\n${idea.trim()}`,
      });
      setJobId(job.id);
      setPlan(
        "Job dispatched. Open the job detail for planner → executor → reviewer output. Checklist updated."
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPlan(
        [
          "## Local fallback plan",
          "1. Planner: success criteria + steps",
          "2. Executor firmware package under firmware/",
          "3. Reviewer evals",
          "4. Host job + SaaS console surface",
          "5. Integrate into apps you sell",
        ].join("\n")
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Idea → Agentic</h1>
      <p className="lede">
        Drop a product idea; we create checklist items and dispatch a team job to
        draft the agent plan.
      </p>
      <form className="card" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="idea">Your idea</label>
          <textarea
            id="idea"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="e.g. Support agent that triages tickets and opens PRs"
            required
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Building plan…" : "Generate agentic plan"}
        </button>
      </form>
      {error && (
        <div className="status-banner error" style={{ marginTop: "1rem" }}>
          Host unavailable — showing fallback skeleton. {error}
        </div>
      )}
      {plan && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{plan}</pre>
          {jobId && (
            <p style={{ marginTop: "0.75rem" }}>
              <Link to={`/jobs/${jobId}`}>Open job {jobId.slice(0, 8)}…</Link>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
