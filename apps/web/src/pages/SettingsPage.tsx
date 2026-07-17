import { useState } from "react";
import { Link } from "react-router-dom";
import { health, loadBackendConfigLocal } from "../lib/api";
import { useSettings, type DbMode } from "../state/settings";
import { ThemeSwitcher } from "../components/ThemeSwitcher";

export function SettingsPage() {
  const { settings, setSettings, resetSettings } = useSettings();
  const [probe, setProbe] = useState<string | null>(null);
  const backend = loadBackendConfigLocal();

  async function testHost() {
    try {
      const h = await health(settings);
      setProbe(`OK · version ${h.version}`);
    } catch (e) {
      setProbe(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div>
      <h1>Settings</h1>
      <p className="lede">
        Host, database mode, backends, Tailscale, and theme. Onboarding config is
        also stored for agents.
      </p>

      {backend && (
        <div className="status-banner ok">
          Onboarding saved: <strong>{backend.company || "workspace"}</strong> ·{" "}
          {backend.db}
          {backend.domain ? ` · ${backend.domain}` : ""}
        </div>
      )}

      <div className="grid-2">
        <div className="card">
          <h2>Host API</h2>
          <div className="field">
            <label htmlFor="hostUrl">Host URL</label>
            <input
              id="hostUrl"
              placeholder="(empty = Vite proxy → :8080)"
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
