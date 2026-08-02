"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/* ── Types mirroring the runtime host contract ──────────────────── */

type RuntimeTeam = { slug: string; name: string; description?: string };

type RuntimeJob = {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  mode?: string;
  error?: string | null;
  result?: {
    summary?: string;
    review_passed?: boolean;
    iterations?: number;
    output?: {
      answer?: string;
      mode?: string;
      workdir?: string;
      files_changed?: string[];
      diff?: string;
    };
  } | null;
};

type Probe = "checking" | "online" | "offline";

const TERMINAL = ["succeeded", "failed", "cancelled"];

/* ── Console ────────────────────────────────────────────────────── */

export function RunConsole() {
  const [probe, setProbe] = useState<Probe>("checking");
  const [teams, setTeams] = useState<RuntimeTeam[]>([]);
  const [team, setTeam] = useState<string>("");
  const [goal, setGoal] = useState("");
  const [mode, setMode] = useState<"chat" | "code">("code");
  const [workdir, setWorkdir] = useState("");
  const [dispatching, setDispatching] = useState(false);
  const [dispatchError, setDispatchError] = useState<string | null>(null);
  const [job, setJob] = useState<RuntimeJob | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const startedAt = useRef<number | null>(null);

  const probeRuntime = useCallback(async () => {
    setProbe("checking");
    try {
      const res = await fetch("/api/run?teams=1");
      if (!res.ok) throw new Error("offline");
      const json = await res.json();
      const list: RuntimeTeam[] = (json.teams || []).map((t: Record<string, unknown>) => ({
        slug: String(t.slug || ""),
        name: String(t.name || t.slug || ""),
        description: String(t.description || ""),
      }));
      setTeams(list);
      if (list.length > 0 && !list.some((t) => t.slug === team)) setTeam(list[0].slug);
      setProbe("online");
    } catch {
      setProbe("offline");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    probeRuntime();
  }, [probeRuntime]);

  /* Poll the active job until it reaches a terminal state */
  const running = job !== null && !TERMINAL.includes(job.status);
  useEffect(() => {
    if (!job || !running) return;
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`/api/run?id=${job.id}`);
        if (!res.ok) return;
        const fresh: RuntimeJob = await res.json();
        setJob(fresh);
      } catch {
        /* transient poll failure — keep trying until terminal */
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [job, running]);

  useEffect(() => {
    if (!running) return;
    const tick = setInterval(() => {
      if (startedAt.current) setElapsed(Math.round((Date.now() - startedAt.current) / 1000));
    }, 1000);
    return () => clearInterval(tick);
  }, [running]);

  async function dispatch() {
    setDispatching(true);
    setDispatchError(null);
    setJob(null);
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ team, goal, mode, ...(mode === "code" && workdir ? { workdir } : {}) }),
      });
      const json = await res.json();
      if (!res.ok) {
        setDispatchError(json.hint || json.error || `Dispatch failed (${res.status})`);
        if (json.error === "runtime_offline") setProbe("offline");
        return;
      }
      startedAt.current = Date.now();
      setElapsed(0);
      setJob({ id: json.job_id, status: json.status || "queued", mode: json.mode });
    } catch {
      setDispatchError("Dispatch request failed.");
    } finally {
      setDispatching(false);
    }
  }

  /* ── Offline: error state with the action that fixes it ──────── */
  if (probe === "offline") {
    return (
      <div className="glass animate-fade-up p-10 text-center">
        <div className="animate-float-y mb-3 font-mono text-4xl text-neon-rose/60">⏻</div>
        <p className="text-sm font-semibold text-slate-200">Runtime host is not reachable</p>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-slate-400">
          The Command Deck dispatches runs to the T-Ex runtime host. Start it, then retry:
        </p>
        <pre className="mx-auto mt-4 max-w-xl overflow-x-auto rounded-lg border border-line bg-black/30 p-4 text-left font-mono text-xs leading-relaxed text-slate-300">
          {`cd runtime
source .venv/bin/activate
python -m texllm.cli serve   # host on :3006`}
        </pre>
        <p className="mt-3 font-mono text-[11px] text-slate-500">
          Elsewhere? Point TEX_RUNTIME_URL (and TEX_RUNTIME_API_KEY) at it in dashboard/.env.local
        </p>
        <button
          onClick={probeRuntime}
          className="mt-5 rounded-lg border border-neon-cyan/40 bg-neon-cyan/10 px-5 py-2.5 text-sm font-semibold text-neon-cyan transition-all hover:bg-neon-cyan/20 hover:shadow-[0_0_24px_-4px_rgba(34,211,238,0.5)]"
        >
          Retry connection
        </button>
      </div>
    );
  }

  /* ── Checking: loading skeleton ───────────────────────────────── */
  if (probe === "checking") {
    return (
      <div className="space-y-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="glass animate-pulse p-6">
            <div className="h-4 w-1/3 rounded bg-white/10" />
            <div className="mt-3 h-3 w-2/3 rounded bg-white/5" />
          </div>
        ))}
      </div>
    );
  }

  const result = job?.result;
  const output = result?.output;

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      {/* Dispatch form */}
      <div className="glass scan-card animate-fade-up p-6 lg:col-span-2">
        <h2 className="mb-1 text-lg font-bold text-white">Command a team. Get real work back.</h2>
        <p className="mb-5 text-sm leading-relaxed text-slate-400">
          Code mode drives a headless coding agent that edits files and returns the diff. Draft mode returns a
          reviewed text answer only.
        </p>

        <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-[0.18em] text-slate-400">Team</label>
        <div className="mb-4 flex flex-wrap gap-2">
          {teams.map((t) => (
            <button
              key={t.slug}
              onClick={() => setTeam(t.slug)}
              title={t.description}
              className={`rounded-full border px-3 py-1.5 font-mono text-xs transition-all ${
                team === t.slug
                  ? "border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan"
                  : "border-line text-slate-400 hover:border-neon-cyan/30 hover:text-slate-200"
              }`}
            >
              {t.slug}
            </button>
          ))}
          {teams.length === 0 && (
            <span className="text-sm text-slate-500">No teams in the runtime workspace yet — run `tex teams` once.</span>
          )}
        </div>

        <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-[0.18em] text-slate-400">Goal</label>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          rows={4}
          placeholder="e.g. Create a FastAPI /healthz endpoint with a test"
          className="mb-4 w-full resize-y rounded-lg border border-line bg-black/30 px-4 py-3 text-sm leading-relaxed text-white outline-none transition-all placeholder:text-slate-600 focus:border-neon-cyan/50 focus:shadow-[0_0_20px_-6px_rgba(34,211,238,0.4)]"
        />

        <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-[0.18em] text-slate-400">Mode</label>
        <div className="mb-4 grid grid-cols-2 gap-2">
          {(
            [
              ["code", "Code — real edits + diff"],
              ["chat", "Draft — text only"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              onClick={() => setMode(value)}
              className={`rounded-lg border px-3 py-2.5 text-left text-xs font-semibold transition-all ${
                mode === value
                  ? "border-neon-violet/50 bg-neon-violet/10 text-neon-violet"
                  : "border-line text-slate-400 hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {mode === "code" && (
          <>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-[0.18em] text-slate-400">
              Workdir (optional)
            </label>
            <input
              value={workdir}
              onChange={(e) => setWorkdir(e.target.value)}
              placeholder="blank = isolated .texllm/runs/<job-id>/ on the host"
              className="mb-2 w-full rounded-lg border border-line bg-black/30 px-4 py-2.5 font-mono text-xs text-white outline-none transition-all placeholder:text-slate-600 focus:border-neon-violet/50"
            />
            <p className="mb-4 font-mono text-[11px] leading-relaxed text-slate-500">
              Code mode needs the `claude` CLI on the runtime host — the job fails with a clear error if it&apos;s
              missing, it never silently falls back to prose.
            </p>
          </>
        )}

        <button
          onClick={dispatch}
          disabled={dispatching || running || !goal.trim() || !team}
          className="w-full rounded-lg border border-neon-cyan/40 bg-gradient-to-r from-neon-cyan/15 to-neon-violet/15 px-6 py-3.5 text-sm font-bold tracking-wide text-neon-cyan transition-all hover:from-neon-cyan/25 hover:to-neon-violet/25 hover:shadow-[0_0_32px_-6px_rgba(34,211,238,0.5)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {dispatching ? "Dispatching…" : running ? "Run in progress…" : "▶ Dispatch run"}
        </button>
        {dispatchError && (
          <div className="mt-4 rounded-lg border border-neon-rose/30 bg-neon-rose/10 px-4 py-3 text-sm text-neon-rose">
            {dispatchError}
          </div>
        )}
      </div>

      {/* Live run / result panel */}
      <div className="glass animate-fade-up p-6 lg:col-span-3" style={{ animationDelay: "120ms" }}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-300">Run Monitor</h2>
          {job && (
            <span
              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider ${
                job.status === "succeeded"
                  ? "border-neon-lime/40 bg-neon-lime/10 text-neon-lime"
                  : job.status === "failed"
                    ? "border-neon-rose/40 bg-neon-rose/10 text-neon-rose"
                    : "border-neon-cyan/40 bg-neon-cyan/10 text-neon-cyan"
              }`}
            >
              <span className={`status-dot ${TERMINAL.includes(job.status) ? "" : "live"}`} />
              {job.status}
            </span>
          )}
        </div>

        {!job && (
          <div className="py-14 text-center">
            <div className="animate-float-y mb-3 font-mono text-4xl text-neon-cyan/60">▶</div>
            <p className="text-sm text-slate-400">No run yet. Pick a team, state the goal, dispatch.</p>
            <p className="mt-1.5 font-mono text-[11px] text-slate-600">
              planner → executor ({mode === "code" ? "coding agent" : "draft"}) → reviewer → integrator
            </p>
          </div>
        )}

        {job && !TERMINAL.includes(job.status) && (
          <div className="py-10 text-center">
            <div className="mb-3 font-mono text-3xl text-neon-cyan animate-pulse">⟳</div>
            <p className="text-sm text-slate-300">
              Team <span className="font-mono text-neon-cyan">{team}</span> is working…{" "}
              <span className="font-mono text-slate-500">{elapsed}s</span>
            </p>
            <p className="mt-1.5 font-mono text-[11px] text-slate-500">
              job {job.id.slice(0, 8)} · {job.mode || mode} mode · polling every 2s
            </p>
          </div>
        )}

        {job && job.status === "failed" && (
          <div className="space-y-4">
            <div className="rounded-lg border border-neon-rose/30 bg-neon-rose/10 px-4 py-3 text-sm text-neon-rose">
              {job.error || "Run failed without an error message."}
            </div>
            <button
              onClick={dispatch}
              className="rounded-lg border border-line px-4 py-2 font-mono text-xs text-slate-300 transition-all hover:border-neon-cyan/40 hover:text-neon-cyan"
            >
              Retry with same goal
            </button>
          </div>
        )}

        {job && job.status === "succeeded" && result && (
          <div className="space-y-4">
            <div>
              <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">Summary</div>
              <p className="text-sm leading-relaxed text-slate-200">{result.summary || "—"}</p>
              <p className="mt-1.5 font-mono text-[11px] text-slate-500">
                review {result.review_passed ? "passed" : "not passed"} · {result.iterations ?? "?"} iterations
              </p>
            </div>

            {output?.mode === "code" ? (
              <>
                <div>
                  <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">
                    Files changed ({output.files_changed?.length ?? 0}) · workdir{" "}
                    <span className="text-slate-400">{output.workdir}</span>
                  </div>
                  <ul className="space-y-1">
                    {(output.files_changed || []).slice(0, 30).map((f) => (
                      <li key={f} className="font-mono text-xs text-neon-lime">
                        + {f}
                      </li>
                    ))}
                    {(output.files_changed || []).length === 0 && (
                      <li className="text-sm text-slate-500">No files changed.</li>
                    )}
                  </ul>
                </div>
                <div>
                  <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">Diff</div>
                  <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap rounded-lg border border-line bg-black/30 p-4 font-mono text-xs leading-relaxed text-slate-300">
                    {output.diff?.trim() || "— no textual diff —"}
                  </pre>
                </div>
              </>
            ) : (
              <div>
                <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">Answer</div>
                <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap rounded-lg border border-line bg-black/30 p-4 font-mono text-xs leading-relaxed text-slate-300">
                  {output?.answer?.trim() || result.summary || "— empty —"}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
