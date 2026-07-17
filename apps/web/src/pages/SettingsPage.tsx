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
  setDefaultAuthProfile,
  upsertAuthProfile,
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
  const [authNotes, setAuthNotes] = useState<string[]>([]);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authMsg, setAuthMsg] = useState<string | null>(null);
  const [cliProbe, setCliProbe] = useState<string | null>(null);
  const [newProfile, setNewProfile] = useState({
    id: "openai-default",
    provider: "openai",
    method: "api_key",
    label: "OpenAI-compatible key",
    base_url: "https://api.openai.com/v1",
    model: "",
    api_key: "",
    agent_id: "claude",
  });

  async function refreshAuth() {
    try {
      const r = await listAuthProfiles(settings);
      setProfiles(r.profiles || []);
      setDefaultProfileId(r.default_profile_id);
      setAuthNotes(r.honest_notes || []);
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
        setAuthNotes(r.honest_notes || []);
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

      {/* Provider auth — OpenClaw-style profiles */}
      <div className="card" style={{ marginBottom: "1rem" }}>
        <h2>Provider auth (API keys & CLI sessions)</h2>
        <p className="empty-hint" style={{ marginBottom: "0.75rem" }}>
          OpenClaw-style: use official <strong>API keys</strong>, or reuse a{" "}
          <strong>local CLI login</strong> on this host (Claude Code / Codex /
          Gemini). We do <strong>not</strong> scrape ChatGPT/Claude browser
          cookies. Full guide:{" "}
          <span className="mono">docs/AUTH.md</span>
        </p>

        {authNotes.length > 0 && (
          <ul style={{ marginTop: 0, color: "var(--tex-muted)", fontSize: "0.88rem" }}>
            {authNotes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}

        <div className="btn-row" style={{ marginTop: 0 }}>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void refreshAuth()}>
            Refresh profiles
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={async () => {
              try {
                const s = await cliAuthStatus(settings, "claude");
                setCliProbe(JSON.stringify(s, null, 2));
              } catch (e) {
                setCliProbe(e instanceof Error ? e.message : String(e));
              }
            }}
          >
            Probe Claude CLI session
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={async () => {
              try {
                const s = await cliAuthStatus(settings, "codex");
                setCliProbe(JSON.stringify(s, null, 2));
              } catch (e) {
                setCliProbe(e instanceof Error ? e.message : String(e));
              }
            }}
          >
            Probe Codex CLI
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
                <th>ID</th>
                <th>Provider</th>
                <th>Method</th>
                <th>Key?</th>
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
                  <td>{p.provider}</td>
                  <td>
                    <span className="chip">{p.method}</span>
                    {p.agent_id ? (
                      <span className="mono"> {p.agent_id}</span>
                    ) : null}
                  </td>
                  <td>{p.has_api_key ? "yes" : p.method === "local_cli" ? "CLI" : "no"}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={async () => {
                        await setDefaultAuthProfile(settings, p.id);
                        setDefaultProfileId(p.id);
                        setAuthMsg(`Default profile: ${p.id}`);
                      }}
                    >
                      Set default
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

        <h3 style={{ marginTop: "1rem" }}>Add / update profile</h3>
        <div className="grid-2">
          <div className="field">
            <label htmlFor="ap-id">Profile id</label>
            <input
              id="ap-id"
              value={newProfile.id}
              onChange={(e) => setNewProfile((p) => ({ ...p, id: e.target.value }))}
            />
          </div>
          <div className="field">
            <label htmlFor="ap-method">Method</label>
            <select
              id="ap-method"
              value={newProfile.method}
              onChange={(e) =>
                setNewProfile((p) => ({ ...p, method: e.target.value }))
              }
            >
              <option value="api_key">API key (official)</option>
              <option value="local_cli">Local CLI session (OpenClaw-style)</option>
              <option value="oauth_google">Google OAuth (Vertex — configure later)</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="ap-provider">Provider</label>
            <select
              id="ap-provider"
              value={newProfile.provider}
              onChange={(e) =>
                setNewProfile((p) => ({ ...p, provider: e.target.value }))
              }
            >
              <option value="openai">OpenAI / ChatGPT API</option>
              <option value="anthropic">Anthropic / Claude</option>
              <option value="xai">xAI / Grok</option>
              <option value="gemini">Google / Gemini</option>
              <option value="custom">Custom OpenAI-compatible</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="ap-label">Label</label>
            <input
              id="ap-label"
              value={newProfile.label}
              onChange={(e) =>
                setNewProfile((p) => ({ ...p, label: e.target.value }))
              }
            />
          </div>
          {newProfile.method === "api_key" && (
            <>
              <div className="field">
                <label htmlFor="ap-url">Base URL</label>
                <input
                  id="ap-url"
                  value={newProfile.base_url}
                  onChange={(e) =>
                    setNewProfile((p) => ({ ...p, base_url: e.target.value }))
                  }
                  placeholder="https://api.x.ai/v1"
                />
              </div>
              <div className="field">
                <label htmlFor="ap-key">API key (stored on host only)</label>
                <input
                  id="ap-key"
                  type="password"
                  autoComplete="off"
                  value={newProfile.api_key}
                  onChange={(e) =>
                    setNewProfile((p) => ({ ...p, api_key: e.target.value }))
                  }
                  placeholder="sk-… / xai-…"
                />
              </div>
            </>
          )}
          {newProfile.method === "local_cli" && (
            <div className="field">
              <label htmlFor="ap-agent">CLI agent id</label>
              <select
                id="ap-agent"
                value={newProfile.agent_id}
                onChange={(e) =>
                  setNewProfile((p) => ({ ...p, agent_id: e.target.value }))
                }
              >
                <option value="claude">claude (Claude Code)</option>
                <option value="codex">codex</option>
                <option value="gemini">gemini</option>
              </select>
            </div>
          )}
        </div>
        <div className="btn-row">
          <button
            type="button"
            className="btn btn-primary"
            onClick={async () => {
              try {
                await upsertAuthProfile(settings, newProfile);
                setAuthMsg("Profile saved on host (.texllm/credentials.json)");
                setNewProfile((p) => ({ ...p, api_key: "" }));
                await refreshAuth();
              } catch (e) {
                setAuthError(e instanceof Error ? e.message : String(e));
              }
            }}
          >
            Save auth profile
          </button>
          <span className="mono" style={{ fontSize: "0.8rem", color: "var(--tex-muted)" }}>
            GET/PUT /v1/auth/profiles
          </span>
        </div>
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
