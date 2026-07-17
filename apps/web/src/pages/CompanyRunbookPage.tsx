/**
 * T-ex Company Runbook Agent — the actual product.
 * Intent → Domain → Product → Teams → Build → GTM → Deploy
 * Providers: Claude / ChatGPT / Gemini / Grok (API key or OAuth/CLI)
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
  result?: unknown;
};

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
  if (settings.apiKey) headers.set("X-API-Key", settings.apiKey);
  const res = await fetch(`${base(settings)}${path}`, { ...init, headers });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

const PROVIDER_DEFAULTS: Record<
  string,
  { base_url: string; method: string; id: string }
> = {
  claude: {
    id: "claude-key",
    base_url: "https://api.anthropic.com",
    method: "api_key",
  },
  openai: {
    id: "openai-key",
    base_url: "https://api.openai.com/v1",
    method: "api_key",
  },
  gemini: {
    id: "gemini-key",
    base_url: "https://generativelanguage.googleapis.com/v1beta",
    method: "api_key",
  },
  grok: {
    id: "grok-key",
    base_url: "https://api.x.ai/v1",
    method: "api_key",
  },
};

export function CompanyRunbookPage() {
  const { settings } = useSettings();
  const [rb, setRb] = useState<RunbookSnap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState("intent");
  const [company, setCompany] = useState("");
  const [notes, setNotes] = useState("");
  const [domain, setDomain] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  // provider connect
  const [prov, setProv] = useState("claude");
  const [apiKey, setApiKey] = useState("");
  const [claudeToken, setClaudeToken] = useState("");

  const refresh = useCallback(async () => {
    try {
      const data = await api<RunbookSnap>(settings, "/v1/runbook");
      setRb(data);
      setCompany(data.company_name || "");
      if (!selected) setSelected(data.active_phase || "intent");
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [settings, selected]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const phase = rb?.phases.find((p) => p.id === selected);

  async function runPhase() {
    if (!phase) return;
    setBusy(true);
    setMsg(null);
    setError(null);
    try {
      const body: Record<string, string> = {
        notes,
        company_name: company || "[Your Company]",
      };
      if (phase.id === "domain" && domain.trim()) body.domain = domain.trim();
      await api(settings, `/v1/runbook/phases/${phase.id}/run`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setMsg(`Phase “${phase.title}” completed (or drafted).`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function savePlaceholders(e: FormEvent) {
    e.preventDefault();
    if (!phase) return;
    try {
      await api(settings, `/v1/runbook/phases/${phase.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          company_name: company,
          placeholder: phase.placeholder,
          status: phase.status === "done" ? "done" : "ready",
        }),
      });
      setMsg("Placeholders saved.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function connectApiKey() {
    const d = PROVIDER_DEFAULTS[prov];
    if (!d || !apiKey.trim()) return;
    try {
      await upsertAuthProfile(settings, {
        id: d.id,
        provider: prov === "grok" ? "xai" : prov === "claude" ? "anthropic" : prov,
        method: "api_key",
        label: `${prov} API key`,
        base_url: d.base_url,
        api_key: apiKey.trim(),
      });
      await setDefaultAuthProfile(settings, d.id);
      setApiKey("");
      setMsg(`${prov} API key saved as default provider.`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function connectClaudeMax() {
    try {
      await saveClaudeSetupToken(settings, {
        token: claudeToken.trim(),
        set_default: true,
      });
      setClaudeToken("");
      setMsg("Claude Max/Pro setup-token saved.");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function connectClaudeCli() {
    try {
      await useClaudeCli(settings);
      setMsg("Using local Claude Code login.");
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
          ? {
              ...p,
              placeholder: { ...p.placeholder, [key]: value },
            }
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
            Start host: <code>python3 -m texllm.cli serve</code>
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
          <p className="rb-kicker">T-ex product</p>
          <h1>{rb.product}</h1>
          <p className="rb-tagline">{rb.tagline}</p>
        </div>
        <div className="rb-progress-block">
          <div className="rb-progress-label">
            Progress {rb.progress.done}/{rb.progress.total}
          </div>
          <div className="rb-progress-track">
            <div
              className="rb-progress-fill"
              style={{ width: `${rb.progress.pct}%` }}
            />
          </div>
          <div className="rb-company">
            <label htmlFor="co">Company</label>
            <input
              id="co"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="[Your Company]"
            />
          </div>
        </div>
      </header>

      {error && <div className="rb-error">{error}</div>}
      {msg && <div className="rb-ok">{msg}</div>}

      {/* Providers — API key or OAuth/subscription */}
      <section className="rb-card">
        <h2>AI providers — connect when ready</h2>
        <p className="rb-muted">
          Claude · ChatGPT · Gemini · Grok via <strong>API key</strong> or{" "}
          <strong>subscription/OAuth/CLI</strong>. You can fill the whole
          runbook with placeholders first; agent runs use the default profile.
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
            <label>API key ({prov})</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Paste API key"
            />
            <button type="button" className="rb-btn" onClick={() => void connectApiKey()}>
              Save as default
            </button>
          </div>
          {prov === "claude" && (
            <>
              <div className="rb-field">
                <label>Claude Max / Pro setup-token</label>
                <input
                  type="password"
                  value={claudeToken}
                  onChange={(e) => setClaudeToken(e.target.value)}
                  placeholder="claude setup-token output"
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
                Use local Claude Code login
              </button>
            </>
          )}
        </div>
        <p className="rb-muted mono">
          Default profile: {rb.auth_default || "none"} · profiles:{" "}
          {(rb.auth_profiles || []).map((p) => p.id).join(", ") || "—"}
        </p>
      </section>

      <div className="rb-layout">
        {/* Phase rail */}
        <nav className="rb-phases" aria-label="Runbook phases">
          {rb.phases.map((p) => (
            <button
              key={p.id}
              type="button"
              className={
                "rb-phase" +
                (selected === p.id ? " active" : "") +
                (p.status === "done" ? " done" : "")
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

        {/* Phase detail */}
        {phase && (
          <section className="rb-detail">
            <h2>
              {phase.order}. {phase.title}
            </h2>
            <p className="rb-muted">{phase.subtitle}</p>
            <p className="rb-agent">
              Agent: <strong>{phase.agent_role}</strong> · Playbook:{" "}
              <code>{phase.playbook}</code>
            </p>

            <h3>Placeholders (pre-loaded company runbook)</h3>
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
                            updatePlaceholderKey(
                              k,
                              JSON.parse(e.target.value)
                            );
                          } catch {
                            /* keep typing */
                          }
                        }}
                        rows={4}
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
                  <label>Domain / URL (for live review)</label>
                  <input
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    placeholder="example.com"
                  />
                </div>
              )}

              <div className="rb-field">
                <label>Notes for agent run</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Optional context when you run this phase"
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
                  {busy ? "Running…" : "Run phase agent"}
                </button>
                <button
                  type="button"
                  className="rb-btn ghost"
                  onClick={async () => {
                    await api(settings, `/v1/runbook/phases/${phase.id}`, {
                      method: "PATCH",
                      body: JSON.stringify({ status: "done" }),
                    });
                    await refresh();
                  }}
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
                <h3>Last result</h3>
                <pre className="rb-result">
                  {typeof phase.result === "string"
                    ? phase.result
                    : JSON.stringify(phase.result, null, 2)}
                </pre>
              </>
            )}
          </section>
        )}
      </div>

      <footer className="rb-footer">
        <div>
          <strong>CLI / Claude Code</strong>
          <code>tex @T-ex "Start company from intent"</code>
          <code>tex review example.com</code>
          <code>tex export sales</code>
        </div>
        <div className="rb-links">
          <Link to="/workspace">Team workspace</Link>
          <Link to="/settings">Settings</Link>
          <Link to="/console">Runtime console</Link>
        </div>
      </footer>
    </div>
  );
}
