import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  cliAuthStatus,
  deleteAuthProfile,
  getAliases,
  health,
  listAuthProfiles,
  loadBackendConfigLocal,
  putAliases,
  saveClaudeSetupToken,
  setDefaultAuthProfile,
  useClaudeCli,
  upsertAuthProfile,
  getAuthRuntime,
  type AgentAliases,
  type AuthProfile,
} from "../lib/api";
import { useSettings, type DbMode } from "../state/settings";
import { ThemeSwitcher } from "../components/ThemeSwitcher";

const DEFAULT_ALIASES: AgentAliases = {
  agent_name: "Tex",
  user_name: "Operator",
  agent_aliases: [],
  user_aliases: [],
};

function listToText(list: string[]) {
  return list.join(", ");
}

function textToList(text: string) {
  return text
    .split(/[,;\n]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function SettingsPage() {
  const { settings, setSettings, resetSettings } = useSettings();
  const [probe, setProbe] = useState<string | null>(null);
  const backend = loadBackendConfigLocal();

  const [aliases, setAliases] = useState<AgentAliases>(DEFAULT_ALIASES);
  const [agentAliasText, setAgentAliasText] = useState("");
  const [userAliasText, setUserAliasText] = useState("");
  const [aliasStatus, setAliasStatus] = useState<string | null>(null);
  const [aliasError, setAliasError] = useState<string | null>(null);
  const [aliasSaving, setAliasSaving] = useState(false);

  const [profiles, setProfiles] = useState<AuthProfile[]>([]);
  const [defaultProfileId, setDefaultProfileId] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authMsg, setAuthMsg] = useState<string | null>(null);
  const [cliProbe, setCliProbe] = useState<string | null>(null);
  const [claudeToken, setClaudeToken] = useState("");
  const [runtimeInfo, setRuntimeInfo] = useState<string | null>(null);
  const [apiKeyDraft, setApiKeyDraft] = useState({
    id: "anthropic-key",
    provider: "anthropic",
    base_url: "https://api.anthropic.com",
    model: "claude-sonnet-4-20250514",
    api_key: "",
    label: "Anthropic API key",
  });

  async function refreshAuth() {
    try {
      const r = await listAuthProfiles(settings);
      setProfiles(r.profiles || []);
      setDefaultProfileId(r.default_profile_id);
      setAuthError(null);
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const a = await getAliases(settings);
        if (!alive) return;
        setAliases(a);
        setAgentAliasText(listToText(a.agent_aliases || []));
        setUserAliasText(listToText(a.user_aliases || []));
        setAliasError(null);
      } catch (e) {
        if (!alive) return;
        setAliasError(
          e instanceof Error
            ? e.message
            : "Could not load aliases from host (using defaults until save)."
        );
      }
      try {
        const r = await listAuthProfiles(settings);
        if (!alive) return;
        setProfiles(r.profiles || []);
        setDefaultProfileId(r.default_profile_id);
      } catch (e) {
        if (!alive) return;
        setAuthError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      alive = false;
    };
  }, [settings]);

  async function testHost() {
    try {
      const h = await health(settings);
      setProbe(`OK · version ${h.version}`);
    } catch (e) {
      setProbe(e instanceof Error ? e.message : String(e));
    }
  }

  async function saveAliases(e: FormEvent) {
    e.preventDefault();
    setAliasSaving(true);
    setAliasStatus(null);
    setAliasError(null);
    const body: AgentAliases = {
      agent_name: aliases.agent_name.trim() || "Tex",
      user_name: aliases.user_name.trim() || "Operator",
      agent_aliases: textToList(agentAliasText),
      user_aliases: textToList(userAliasText),
    };
    try {
      const saved = await putAliases(settings, body);
      setAliases(saved);
      setAgentAliasText(listToText(saved.agent_aliases || []));
      setUserAliasText(listToText(saved.user_aliases || []));
      setAliasStatus("Aliases saved on host (used in chat, jobs, and local CLI spawn).");
      localStorage.setItem("texllm.aliases.v1", JSON.stringify(saved));
    } catch (err) {
      setAliasError(err instanceof Error ? err.message : String(err));
    } finally {
      setAliasSaving(false);
    }
  }

  return (
    <div>
      <h1>Settings</h1>
      <p className="lede">
        Host, agent names, database, backends, Tailscale, and theme.
      </p>

      {backend && (
        <div className="status-banner ok">
          Onboarding saved: <strong>{backend.company || "workspace"}</strong> ·{" "}
          {backend.db}
          {backend.domain ? ` · ${backend.domain}` : ""}
        </div>
      )}

      {/* Claude-first only */}
      <div className="card" style={{ marginBottom: "1rem" }}>
        <h2>Claude only (first path)</h2>
        <p className="empty-hint" style={{ marginBottom: "0.85rem" }}>
          Chat + Jobs use the <strong>default Claude profile</strong>. See{" "}
          <span className="mono">docs/CLAUDE-FIRST.md</span>
        </p>

        <div className="grid-2">
          <div className="card" style={{ background: "var(--tex-surface-2)", boxShadow: "none" }}>
            <h3>1) Claude Max / Pro setup-token</h3>
            <p className="empty-hint">
              Run <span className="mono">claude setup-token</span> → paste. Host
              runs <span className="mono">claude -p</span> with that token.
            </p>
            <div className="field">
              <label htmlFor="claude-tok">Setup token</label>
              <textarea
                id="claude-tok"
                value={claudeToken}
                onChange={(e) => setClaudeToken(e.target.value)}
                placeholder="Paste token from claude setup-token"
                rows={3}
              />
            </div>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={async () => {
                try {
                  await saveClaudeSetupToken(settings, {
                    token: claudeToken.trim(),
                    profile_id: "claude-max",
                    set_default: true,
                  });
                  setClaudeToken("");
                  setAuthMsg("Claude Max/Pro setup-token saved & set default");
                  await refreshAuth();
                  const rt = await getAuthRuntime(settings);
                  setRuntimeInfo(JSON.stringify(rt, null, 2));
                } catch (e) {
                  setAuthError(e instanceof Error ? e.message : String(e));
                }
              }}
            >
              Save Claude Max token
            </button>
          </div>

          <div className="card" style={{ background: "var(--tex-surface-2)", boxShadow: "none" }}>
            <h3>2) Local Claude Code login</h3>
            <p className="empty-hint">
              On the host: <span className="mono">claude auth login</span>
            </p>
            <div className="btn-row">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={async () => {
                  try {
                    const r = await useClaudeCli(settings);
                    setAuthMsg("Default = Claude Code CLI session");
                    setCliProbe(JSON.stringify(r.cli_status, null, 2));
                    await refreshAuth();
                    const rt = await getAuthRuntime(settings);
                    setRuntimeInfo(JSON.stringify(rt, null, 2));
                  } catch (e) {
                    setAuthError(e instanceof Error ? e.message : String(e));
                  }
                }}
              >
                Use local Claude CLI
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={async () => {
                  const s = await cliAuthStatus(settings, "claude");
                  setCliProbe(JSON.stringify(s, null, 2));
                }}
              >
                Probe CLI status
              </button>
            </div>
          </div>

          <div className="card" style={{ background: "var(--tex-surface-2)", boxShadow: "none" }}>
            <h3>3) Anthropic API key</h3>
            <p className="empty-hint">
              Console key <span className="mono">sk-ant-…</span>
            </p>
            <div className="field">
              <label htmlFor="ak-key">API key</label>
              <input
                id="ak-key"
                type="password"
                autoComplete="off"
                value={apiKeyDraft.api_key}
                onChange={(e) =>
                  setApiKeyDraft((p) => ({ ...p, api_key: e.target.value }))
                }
                placeholder="sk-ant-…"
              />
            </div>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={async () => {
                await upsertAuthProfile(settings, {
                  ...apiKeyDraft,
                  method: "api_key",
                  provider: "anthropic",
                });
                await setDefaultAuthProfile(settings, apiKeyDraft.id);
                setApiKeyDraft((p) => ({ ...p, api_key: "" }));
                setAuthMsg("Anthropic API key saved & default");
                await refreshAuth();
                const rt = await getAuthRuntime(settings);
                setRuntimeInfo(JSON.stringify(rt, null, 2));
              }}
            >
              Save Anthropic API key
            </button>
          </div>

          <div className="card" style={{ background: "var(--tex-surface-2)", boxShadow: "none" }}>
            <h3>Active runtime</h3>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={async () => {
                try {
                  const rt = await getAuthRuntime(settings);
                  setRuntimeInfo(JSON.stringify(rt, null, 2));
                } catch (e) {
                  setAuthError(e instanceof Error ? e.message : String(e));
                }
              }}
            >
              Refresh runtime
            </button>
            {runtimeInfo && (
              <pre className="mono" style={{ whiteSpace: "pre-wrap", fontSize: "0.78rem" }}>
                {runtimeInfo}
              </pre>
            )}
          </div>
        </div>

        <div className="btn-row">
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void refreshAuth()}>
            Refresh profiles
          </button>
        </div>

        {cliProbe && (
          <pre className="mono" style={{ whiteSpace: "pre-wrap", fontSize: "0.78rem" }}>
            {cliProbe}
          </pre>
        )}

        {profiles.length > 0 && (
          <table className="data-table" style={{ marginTop: "0.75rem" }}>
            <thead>
              <tr>
                <th>Profile</th>
                <th>Method</th>
                <th>Secret?</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {profiles.map((p) => (
                <tr key={p.id}>
                  <td>
                    <strong>{p.label || p.id}</strong>
                    {defaultProfileId === p.id && (
                      <span className="chip ok" style={{ marginLeft: 6 }}>
                        default
                      </span>
                    )}
                  </td>
                  <td>
                    <span className="chip">{p.method}</span>
                  </td>
                  <td>
                    {p.has_secret || p.has_api_key
                      ? "yes"
                      : p.method === "local_cli"
                        ? "CLI"
                        : "no"}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={async () => {
                        await setDefaultAuthProfile(settings, p.id);
                        setDefaultProfileId(p.id);
                        setAuthMsg(`Default: ${p.id}`);
                      }}
                    >
                      Default
                    </button>{" "}
                    <button
                      type="button"
                      className="btn btn-sm btn-ghost"
                      onClick={async () => {
                        await deleteAuthProfile(settings, p.id);
                        await refreshAuth();
                      }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {authMsg && (
          <div className="status-banner ok" style={{ marginTop: "0.75rem" }}>
            {authMsg}
          </div>
        )}
        {authError && (
          <div className="status-banner error" style={{ marginTop: "0.75rem" }} role="alert">
            {authError}
          </div>
        )}
      </div>

      {/* Agent aliases */}
      <form className="card" onSubmit={saveAliases} style={{ marginBottom: "1rem" }}>
        <h2>Agent aliases</h2>
        <p className="empty-hint" style={{ marginBottom: "0.85rem" }}>
          Control how you and the agent address each other. Stored via{" "}
          <span className="mono">PUT /v1/settings/aliases</span> and applied to
          chat, team jobs, and local CLI prompts.
        </p>

        <div className="grid-2">
          <div className="field">
            <label htmlFor="agent_name">What you call the agent</label>
            <input
              id="agent_name"
              value={aliases.agent_name}
              onChange={(e) =>
                setAliases((a) => ({ ...a, agent_name: e.target.value }))
              }
              placeholder="e.g. Tex, Alli, Nova"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="user_name">What the agent calls you</label>
            <input
              id="user_name"
              value={aliases.user_name}
              onChange={(e) =>
                setAliases((a) => ({ ...a, user_name: e.target.value }))
              }
              placeholder="e.g. Robeul, Captain, Operator"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="agent_aliases">Other names for the agent (comma-separated)</label>
            <input
              id="agent_aliases"
              value={agentAliasText}
              onChange={(e) => setAgentAliasText(e.target.value)}
              placeholder="Assistant, Bot, Helper"
            />
          </div>
          <div className="field">
            <label htmlFor="user_aliases">Other names for you (comma-separated)</label>
            <input
              id="user_aliases"
              value={userAliasText}
              onChange={(e) => setUserAliasText(e.target.value)}
              placeholder="you, boss, team lead"
            />
          </div>
        </div>

        <div
          className="card"
          style={{
            marginTop: "0.25rem",
            background: "var(--tex-surface-2)",
            boxShadow: "none",
          }}
        >
          <strong>Preview</strong>
          <p className="empty-hint" style={{ margin: "0.35rem 0 0" }}>
            You: “Hey <strong>{aliases.agent_name || "Tex"}</strong>, …”
            <br />
            Agent: “Sure, <strong>{aliases.user_name || "Operator"}</strong>, …”
          </p>
        </div>

        <div className="btn-row">
          <button className="btn btn-primary" type="submit" disabled={aliasSaving}>
            {aliasSaving ? "Saving…" : "Save aliases"}
          </button>
          <span className="mono" style={{ color: "var(--tex-muted)", fontSize: "0.8rem" }}>
            GET/PUT /v1/settings/aliases
          </span>
        </div>
        {aliasStatus && (
          <div className="status-banner ok" style={{ marginTop: "0.75rem" }}>
            {aliasStatus}
          </div>
        )}
        {aliasError && (
          <div className="status-banner error" style={{ marginTop: "0.75rem" }} role="alert">
            {aliasError}
          </div>
        )}
      </form>

      <div className="grid-2">
        <div className="card">
          <h2>Host API</h2>
          <div className="field">
            <label htmlFor="hostUrl">Host URL</label>
            <input
              id="hostUrl"
              placeholder="(empty = same origin / Vite proxy → :3006)"
              value={settings.hostUrl}
              onChange={(e) => setSettings({ hostUrl: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="apiKey">API key</label>
            <input
              id="apiKey"
              value={settings.apiKey}
              onChange={(e) => setSettings({ apiKey: e.target.value })}
            />
          </div>
          <div className="btn-row">
            <button
              className="btn btn-primary"
              type="button"
              onClick={() => void testHost()}
            >
              Probe /health
            </button>
          </div>
          {probe && (
            <div className="status-banner" style={{ marginTop: "0.75rem" }}>
              {probe}
            </div>
          )}
        </div>

        <div className="card">
          <h2>Theme</h2>
          <ThemeSwitcher />
        </div>

        <div className="card">
          <h2>Database</h2>
          <div className="field">
            <label htmlFor="dbMode">Mode</label>
            <select
              id="dbMode"
              value={settings.dbMode}
              onChange={(e) =>
                setSettings({ dbMode: e.target.value as DbMode })
              }
            >
              <option value="none">None (in-memory host)</option>
              <option value="postgres">PostgreSQL</option>
              <option value="supabase">Supabase</option>
            </select>
          </div>
          {settings.dbMode === "postgres" && (
            <div className="field">
              <label htmlFor="databaseUrl">DATABASE_URL</label>
              <input
                id="databaseUrl"
                value={settings.databaseUrl}
                onChange={(e) => setSettings({ databaseUrl: e.target.value })}
                placeholder="postgres://user:pass@localhost:5432/texllm"
              />
            </div>
          )}
          {settings.dbMode === "supabase" && (
            <>
              <div className="field">
                <label htmlFor="supaUrl">Supabase URL</label>
                <input
                  id="supaUrl"
                  value={settings.supabaseUrl}
                  onChange={(e) =>
                    setSettings({ supabaseUrl: e.target.value })
                  }
                />
              </div>
              <div className="field">
                <label htmlFor="supaKey">Anon key</label>
                <input
                  id="supaKey"
                  value={settings.supabaseAnonKey}
                  onChange={(e) =>
                    setSettings({ supabaseAnonKey: e.target.value })
                  }
                />
              </div>
            </>
          )}
        </div>

        <div className="card">
          <h2>NocoBase & Tailscale</h2>
          <div className="field">
            <label htmlFor="noco">NocoBase URL</label>
            <input
              id="noco"
              value={settings.nocobaseUrl}
              onChange={(e) => setSettings({ nocobaseUrl: e.target.value })}
              placeholder="http://127.0.0.1:13000"
            />
          </div>
          <div className="field">
            <label htmlFor="ts">Tailscale hostname</label>
            <input
              id="ts"
              value={settings.tailscaleHostname}
              onChange={(e) =>
                setSettings({ tailscaleHostname: e.target.value })
              }
              placeholder="tex-host.tailnet.ts.net"
            />
          </div>
          {settings.tailscaleHostname && (
            <p className="mono">ssh {settings.tailscaleHostname}</p>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <h2>Onboarding</h2>
        <div className="btn-row">
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => setSettings({ onboarded: false })}
          >
            Mark not onboarded
          </button>
          <Link className="btn btn-ghost" to="/onboarding">
            Open wizard
          </Link>
          <button className="btn btn-ghost" type="button" onClick={resetSettings}>
            Reset settings
          </button>
        </div>
      </div>
    </div>
  );
}
