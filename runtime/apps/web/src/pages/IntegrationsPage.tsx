import { useCallback, useEffect, useState } from "react";
import { useSettings } from "../state/settings";

type AgentRow = {
  id: string;
  binary: string;
  path: string;
  version?: string | null;
  noninteractive: boolean;
  notes: string;
};

type AgentsResponse = {
  count: number;
  agents: AgentRow[];
  execution_modes?: { id: string; description: string }[];
};

export function IntegrationsPage() {
  const { settings } = useSettings();
  const [data, setData] = useState<AgentsResponse | null>(null);
  const [system, setSystem] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [spawnOut, setSpawnOut] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const base = (settings.hostUrl || "").replace(/\/$/, "");

  const headers = useCallback(() => {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (settings.apiKey) h["X-API-Key"] = settings.apiKey;
    return h;
  }, [settings.apiKey]);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [a, s] = await Promise.all([
        fetch(`${base}/v1/agents`, { headers: headers() }).then(async (r) => {
          if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
          return r.json() as Promise<AgentsResponse>;
        }),
        fetch(`${base}/v1/system`).then(async (r) => {
          if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
          return r.json();
        }),
      ]);
      setData(a);
      setSystem(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [base, headers]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function spawn(agentId: string) {
    setBusy(true);
    setSpawnOut(null);
    try {
      const r = await fetch(`${base}/v1/agents/run`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          agent_id: agentId,
          prompt: "Reply with one short sentence: T-ex local CLI OK.",
        }),
      });
      const body = await r.json();
      setSpawnOut(JSON.stringify(body, null, 2));
    } catch (e) {
      setSpawnOut(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Integrations</h1>
      <p className="lede">
        Local terminal AI CLIs are auto-detected from <span className="mono">PATH</span>.
        Spawn uses the CLI’s own login — not <span className="mono">LLM_API_KEY</span>.
      </p>

      {error && (
        <div className="status-banner error" role="alert">
          {error}. Is the host running? Default:{" "}
          <span className="mono">python3 -m texllm.cli serve</span> on port 3006.
        </div>
      )}

      <div className="btn-row" style={{ marginTop: 0 }}>
        <button type="button" className="btn btn-primary" onClick={() => void refresh()}>
          Rescan agents
        </button>
      </div>

      <div className="card" style={{ marginTop: "1rem", overflowX: "auto" }}>
        <h2>Detected terminal agents</h2>
        {!data?.agents?.length && (
          <p className="empty-hint">
            None found. Install Claude Code, Codex, Gemini CLI, etc., and ensure they are on PATH.
          </p>
        )}
        {!!data?.agents?.length && (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Path</th>
                <th>Version</th>
                <th>Non-interactive</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.agents.map((a) => (
                <tr key={a.id}>
                  <td>
                    <strong>{a.id}</strong>
                  </td>
                  <td className="mono">{a.path}</td>
                  <td className="mono">{a.version || "—"}</td>
                  <td>
                    <span className={"chip " + (a.noninteractive ? "ok" : "warn")}>
                      {a.noninteractive ? "yes" : "limited"}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-sm"
                      disabled={busy || !a.noninteractive}
                      onClick={() => void spawn(a.id)}
                    >
                      Test spawn
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {spawnOut && (
        <pre
          className="card mono"
          style={{ marginTop: "1rem", whiteSpace: "pre-wrap", overflow: "auto" }}
        >
          {spawnOut}
        </pre>
      )}

      <div className="card" style={{ marginTop: "1rem" }}>
        <h2>Execution modes</h2>
        <ul>
          {(data?.execution_modes || []).map((m) => (
            <li key={m.id}>
              <strong>{m.id}</strong> — {m.description}
            </li>
          ))}
        </ul>
        {system && Array.isArray((system as { honest_notes?: string[] }).honest_notes) && (
          <>
            <h3>Notes</h3>
            <ul>
              {((system as { honest_notes: string[] }).honest_notes || []).map((n, i) => (
                <li key={i} className="empty-hint">
                  {n}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <h2>Data / ops</h2>
        <p className="empty-hint">
          DB mode in settings: <strong>{settings.dbMode}</strong>
          {settings.tailscaleHostname
            ? ` · Tailscale ${settings.tailscaleHostname}`
            : ""}
          . See docs/REMOTE-ACCESS.md for LAN, Tailscale, and DNS A records.
        </p>
      </div>
    </div>
  );
}
