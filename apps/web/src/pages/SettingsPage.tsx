import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getAliases,
  health,
  loadBackendConfigLocal,
  putAliases,
  type AgentAliases,
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

      {/* Agent aliases — primary new section */}
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
