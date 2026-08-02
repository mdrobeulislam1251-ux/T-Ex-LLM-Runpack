/**
 * T-ex Company Runbook — Intent → Deploy
 * Workable without AI; updates visibly when you run a phase.
 */
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useSettings } from "../state/settings";
import {
  saveClaudeSetupToken,
  upsertAuthProfile,
  setDefaultAuthProfile,
  useClaudeCli,
  type AuthProfile,
} from "../lib/api";

type Phase = {
  id: string;
  order: number;
  title: string;
  subtitle: string;
  agent_role: string;
  status: string;
  placeholder: Record<string, unknown>;
  outputs: string[];
  playbook: string;
  result?: {
    summary?: string;
    content?: string;
    provider?: string;
    auth_method?: string;
    error?: string;
    mode?: string;
  } | null;
};

type Activity = { title: string; detail: string; ts: string };

type RunbookSnap = {
  product: string;
  tagline: string;
  company_name: string;
  active_phase: string;
  phases: Phase[];
  providers: {
    id: string;
    name: string;
    methods: string[];
    hint: string;
  }[];
  progress: { done: number; total: number; pct: number };
  auth_profiles: AuthProfile[];
  auth_default: string | null;
  activity?: Activity[];
  active_ai?: {
    name?: string;
    method?: string;
    provider?: string;
    hint?: string;
    usable?: boolean;
    has_secret?: boolean;
  };
  cli: Record<string, string>;
};

function base(settings: { hostUrl: string; apiKey: string }) {
  return (settings.hostUrl || "").replace(/\/$/, "");
}

async function api<T>(
  settings: { hostUrl: string; apiKey: string },
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  // Always send a key; host accepts "change-me" without strict match
  headers.set("X-API-Key", settings.apiKey || "change-me");
  const res = await fetch(`${base(settings)}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = await res.text();
    try {
      detail = JSON.parse(detail).detail || detail;
    } catch {
      /* keep text */
    }
    throw new Error(String(detail));
  }
  return res.json() as Promise<T>;
}

const PROVIDER_DEFAULTS: Record<
  string,
  { base_url: string; id: string; provider: string }
> = {
  claude: {
    id: "claude-key",
    base_url: "https://api.anthropic.com",
    provider: "anthropic",
  },
  openai: {
    id: "openai-key",
    base_url: "https://api.openai.com/v1",
    provider: "openai",
  },
  gemini: {
    id: "gemini-key",
    base_url: "https://generativelanguage.googleapis.com/v1beta",
    provider: "gemini",
  },
  grok: {
    id: "grok-key",
    base_url: "https://api.x.ai/v1",
    provider: "xai",
  },
};

export function CompanyRunbookPage() {
  const { settings, setSettings } = useSettings();
  const [rb, setRb] = useState<RunbookSnap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState("intent");
  const [company, setCompany] = useState("");
  const [notes, setNotes] = useState("");
  const [domain, setDomain] = useState("");
  const [busy, setBusy] = useState(false);
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const [prov, setProv] = useState("claude");
  const [apiKey, setApiKey] = useState("");
  const [claudeToken, setClaudeToken] = useState("");

  const refresh = useCallback(async () => {
    const data = await api<RunbookSnap>(settings, "/v1/runbook");
    setRb(data);
    setCompany(data.company_name || "");
    setError(null);
    return data;
  }, [settings]);

  useEffect(() => {
    void refresh().catch((e) =>
      setError(e instanceof Error ? e.message : String(e))
    );
  }, [refresh]);

  // Keep API key aligned for local demos
  useEffect(() => {
    if (!settings.apiKey || settings.apiKey === "dev-secret") {
      setSettings({ apiKey: "change-me" });
    }
  }, [settings.apiKey, setSettings]);

  const phase = rb?.phases.find((p) => p.id === selected);

  async function runPhase() {
    if (!phase) return;
    setBusy(true);
    setMsg(null);
    setError(null);
    setStatusLine(`Running “${phase.title}”…`);

    // Optimistic UI: show running
    setRb((prev) =>
      prev
        ? {
            ...prev,
            phases: prev.phases.map((p) =>
              p.id === phase.id ? { ...p, status: "running" } : p
            ),
          }
        : prev
    );

    try {
      const body: Record<string, string> = {
        notes,
        company_name: company || "Your Company",
      };
      if (phase.id === "domain" && domain.trim()) body.domain = domain.trim();

      const snap = await api<RunbookSnap>(
        settings,
        `/v1/runbook/phases/${phase.id}/run`,
        { method: "POST", body: JSON.stringify(body) }
      );
      setRb(snap);
      setCompany(snap.company_name || company);
      const updated = snap.phases.find((p) => p.id === phase.id);
      const summary =
        updated?.result?.summary ||
        `Phase “${phase.title}” marked ${updated?.status || "done"}.`;
      setMsg(summary);
      setStatusLine(
        `Done · provider=${updated?.result?.provider || "?"} · ${
          updated?.result?.auth_method || ""
        }`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatusLine("Failed — see error");
      // reload truth from server
      try {
        await refresh();
      } catch {
        /* ignore */
      }
    } finally {
      setBusy(false);
    }
  }

  async function savePlaceholders(e: FormEvent) {
    e.preventDefault();
    if (!phase) return;
    try {
      const snap = await api<RunbookSnap>(
        settings,
        `/v1/runbook/phases/${phase.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            company_name: company,
            placeholder: phase.placeholder,
            status: phase.status === "done" ? "done" : "ready",
          }),
        }
      );
      setRb(snap);
      setMsg("Placeholders saved — progress bar will move when you Run or Mark done.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function markDoneOnly() {
    if (!phase) return;
    const snap = await api<RunbookSnap>(
      settings,
      `/v1/runbook/phases/${phase.id}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          status: "done",
          company_name: company,
          result: {
            summary: "Marked done without AI",
            content: "User marked this phase done (no model call).",
            mode: "manual",
          },
        }),
      }
    );
    setRb(snap);
    setMsg(`Marked “${phase.title}” done.`);
  }

  async function connectApiKey() {
    const d = PROVIDER_DEFAULTS[prov];
    if (!d || !apiKey.trim()) {
      setError("Paste an API key first.");
      return;
    }
    try {
      await upsertAuthProfile(settings, {
        id: d.id,
        provider: d.provider,
        method: "api_key",
        label: `${prov} API key`,
        base_url: d.base_url,
        api_key: apiKey.trim(),
      });
      await setDefaultAuthProfile(settings, d.id);
      // Host must not force mock
      setApiKey("");
      setMsg(
        `${prov} API key saved and set as default. Check “Active AI now” above — then Run phase agent.`
      );
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function connectClaudeMax() {
    if (!claudeToken.trim()) {
      setError("Paste setup-token from: claude setup-token");
      return;
    }
    try {
      await saveClaudeSetupToken(settings, {
        token: claudeToken.trim(),
        set_default: true,
      });
      setClaudeToken("");
      setMsg("Claude Max token saved. Restart host with LLM_PROVIDER=auto to use it.");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function connectClaudeCli() {
    try {
      await useClaudeCli(settings);
      setMsg(
        "Claude CLI profile set. Host must run with LLM_PROVIDER=auto (not mock) and `claude` on PATH."
      );
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function updatePlaceholderKey(key: string, value: unknown) {
    if (!rb || !phase) return;
    setRb({
      ...rb,
      phases: rb.phases.map((p) =>
        p.id === phase.id
          ? { ...p, placeholder: { ...p.placeholder, [key]: value } }
          : p
      ),
    });
  }

  if (!rb && error) {
    return (
      <div className="runbook">
        <div className="rb-error">
          {error}
          <p className="rb-muted">
            Start: <code>HOST_API_KEY=change-me python3 -m texllm.cli serve</code>
          </p>
        </div>
      </div>
    );
  }

  if (!rb) {
    return (
      <div className="runbook">
        <p className="rb-muted">Loading company runbook…</p>
      </div>
    );
  }

  return (
    <div className="runbook">
      <header className="rb-hero">
        <div>
          <p className="rb-kicker">Product · not a telemetry dashboard</p>
          <h1>{rb.product}</h1>
          <p className="rb-tagline">{rb.tagline}</p>
        </div>
        <div className="rb-progress-block">
          <div className="rb-progress-label">
            Progress {rb.progress.done}/{rb.progress.total} ({rb.progress.pct}%)
          </div>
          <div className="rb-progress-track">
            <div
              className="rb-progress-fill"
              style={{ width: `${rb.progress.pct}%` }}
            />
          </div>
          <div className="rb-company">
            <label htmlFor="co">Company name</label>
            <input
              id="co"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Your Company"
            />
          </div>
          {statusLine && (
            <p className="rb-muted" style={{ marginTop: 8 }}>
              {busy ? "⏳ " : "✓ "}
              {statusLine}
            </p>
          )}
        </div>
      </header>

      {error && <div className="rb-error">{error}</div>}
      {msg && <div className="rb-ok">{msg}</div>}

      {rb.active_ai && (
        <div
          className={
            rb.active_ai.name === "mock" ? "rb-error" : "rb-ok"
          }
          style={{ marginBottom: 16 }}
        >
          <strong>Active AI now:</strong> {rb.active_ai.name}
          {rb.active_ai.provider ? ` (${rb.active_ai.provider})` : ""} ·{" "}
          {rb.active_ai.method || "—"}
          <br />
          {rb.active_ai.hint}
        </div>
      )}

      <section className="rb-card">
        <h2>1) Connect AI — required for real answers</h2>
        <p className="rb-muted">
          <strong>Grok = paste xAI API key</strong> (not “local CLI”). Claude
          can use API key, Max token, or <code>claude auth login</code>. ChatGPT
          / Gemini = API keys.
        </p>
        <div className="rb-providers">
          {rb.providers.map((p) => (
            <button
              key={p.id}
              type="button"
              className={"rb-prov" + (prov === p.id ? " on" : "")}
              onClick={() => setProv(p.id)}
            >
              <strong>{p.name}</strong>
              <span>{p.hint}</span>
            </button>
          ))}
        </div>
        <div className="rb-connect">
          <div className="rb-field">
            <label>API key for {prov}</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                prov === "grok"
                  ? "xai-… API key"
                  : prov === "claude"
                    ? "sk-ant-…"
                    : "API key"
              }
            />
            <button type="button" className="rb-btn" onClick={() => void connectApiKey()}>
              Save API key as default
            </button>
          </div>
          {prov === "claude" && (
            <>
              <div className="rb-field">
                <label>Or Claude Max setup-token</label>
                <input
                  type="password"
                  value={claudeToken}
                  onChange={(e) => setClaudeToken(e.target.value)}
                  placeholder="from: claude setup-token"
                />
                <button
                  type="button"
                  className="rb-btn"
                  onClick={() => void connectClaudeMax()}
                >
                  Save Max token
                </button>
              </div>
              <button
                type="button"
                className="rb-btn ghost"
                onClick={() => void connectClaudeCli()}
              >
                Use local Claude CLI
              </button>
            </>
          )}
        </div>
        <p className="rb-muted mono">
          Default: {rb.auth_default || "none (mock drafts)"} ·{" "}
          {(rb.auth_profiles || []).map((p) => `${p.id}(${p.method})`).join(", ") ||
            "no profiles yet"}
        </p>
        <p className="rb-muted">
          For live models, restart host with{" "}
          <code>LLM_PROVIDER=auto</code> (not mock). Offline: keep mock —{" "}
          <strong>Run phase</strong> still fills placeholders and moves progress.
        </p>
      </section>

      <div className="rb-layout">
        <nav className="rb-phases" aria-label="Runbook phases">
          {rb.phases.map((p) => (
            <button
              key={p.id}
              type="button"
              className={
                "rb-phase" +
                (selected === p.id ? " active" : "") +
                (p.status === "done" ? " done" : "") +
                (p.status === "running" ? " running" : "")
              }
              onClick={() => setSelected(p.id)}
            >
              <span className="num">{p.order}</span>
              <span className="meta">
                <strong>{p.title}</strong>
                <em>{p.status}</em>
              </span>
            </button>
          ))}
        </nav>

        {phase && (
          <section className="rb-detail">
            <h2>
              {phase.order}. {phase.title}
            </h2>
            <p className="rb-muted">{phase.subtitle}</p>
            <p className="rb-agent">
              Agent: <strong>{phase.agent_role}</strong> ·{" "}
              <code>{phase.playbook}</code>
            </p>

            <h3>Placeholders</h3>
            <form onSubmit={savePlaceholders}>
              <div className="rb-placeholders">
                {Object.entries(phase.placeholder || {}).map(([k, v]) => (
                  <div key={k} className="rb-field">
                    <label>{k}</label>
                    {Array.isArray(v) ? (
                      <textarea
                        value={(v as string[]).join("\n")}
                        onChange={(e) =>
                          updatePlaceholderKey(
                            k,
                            e.target.value.split("\n").filter(Boolean)
                          )
                        }
                        rows={3}
                      />
                    ) : typeof v === "object" && v !== null ? (
                      <textarea
                        value={JSON.stringify(v, null, 2)}
                        onChange={(e) => {
                          try {
                            updatePlaceholderKey(k, JSON.parse(e.target.value));
                          } catch {
                            /* typing */
                          }
                        }}
                        rows={3}
                      />
                    ) : (
                      <input
                        value={String(v ?? "")}
                        onChange={(e) =>
                          updatePlaceholderKey(k, e.target.value)
                        }
                      />
                    )}
                  </div>
                ))}
              </div>

              {phase.id === "domain" && (
                <div className="rb-field">
                  <label>Domain / URL (optional live review)</label>
                  <input
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    placeholder="example.com"
                  />
                </div>
              )}

              <div className="rb-field">
                <label>Notes for this run</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Anything the agent should know"
                />
              </div>

              <div className="rb-actions">
                <button type="submit" className="rb-btn ghost">
                  Save placeholders
                </button>
                <button
                  type="button"
                  className="rb-btn primary"
                  disabled={busy}
                  onClick={() => void runPhase()}
                >
                  {busy ? "Running phase…" : "Run phase agent"}
                </button>
                <button
                  type="button"
                  className="rb-btn ghost"
                  disabled={busy}
                  onClick={() => void markDoneOnly()}
                >
                  Mark done (no AI)
                </button>
              </div>
            </form>

            <h3>Expected outputs</h3>
            <ul className="rb-outputs">
              {phase.outputs.map((o) => (
                <li key={o}>{o}</li>
              ))}
            </ul>

            {phase.result != null && (
              <>
                <h3>Result (this updates after Run)</h3>
                <p className="rb-muted">
                  {phase.result.summary || "—"}
                  {phase.result.provider
                    ? ` · provider=${phase.result.provider}`
                    : ""}
                </p>
                <pre className="rb-result">
                  {phase.result.content ||
                    JSON.stringify(phase.result, null, 2)}
                </pre>
              </>
            )}
          </section>
        )}
      </div>

      {(rb.activity || []).length > 0 && (
        <section className="rb-card" style={{ marginTop: 16 }}>
          <h2>Activity (proof of updates)</h2>
          <ul className="rb-outputs">
            {(rb.activity || []).slice(0, 12).map((a, i) => (
              <li key={i}>
                <strong>{a.title}</strong>
                {a.detail ? ` — ${a.detail}` : ""}
                <span className="rb-muted"> · {a.ts}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <footer className="rb-footer">
        <div>
          <strong>CLI</strong>
          <code>tex @T-ex "Start company from intent"</code>
          <code>tex review example.com</code>
        </div>
        <div className="rb-links">
          <Link to="/workspace">Teams</Link>
          <Link to="/settings">Settings</Link>
        </div>
      </footer>
    </div>
  );
}
