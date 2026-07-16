import { useState } from "react";
import { Link } from "react-router-dom";
import { health } from "../lib/api";
import { useSettings, type DbMode } from "../state/settings";

export function SettingsPage() {
  const { settings, setSettings, resetSettings } = useSettings();
  const [probe, setProbe] = useState<string | null>(null);

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
        Host connection, database mode, optional NocoBase admin, and Tailscale
        SSH notes for private ops access.
      </p>

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
            <button className="btn btn-primary" type="button" onClick={() => void testHost()}>
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
          <h2>Database</h2>
          <p style={{ color: "var(--tex-muted)", fontSize: "0.9rem" }}>
            Installer auto-detects Postgres or Supabase. Values here are for
            the console operator profile (persistence wiring lands next).
          </p>
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
          <h2>Lightweight backend (NocoBase)</h2>
          <p style={{ color: "var(--tex-muted)", fontSize: "0.9rem" }}>
            Optional low-code admin pulled by{" "}
            <span className="mono">scripts/install</span>. Paste URL when
            running.
          </p>
          <div className="field">
            <label htmlFor="noco">NocoBase URL</label>
            <input
              id="noco"
              value={settings.nocobaseUrl}
              onChange={(e) => setSettings({ nocobaseUrl: e.target.value })}
              placeholder="http://127.0.0.1:13000"
            />
          </div>
          {settings.nocobaseUrl && (
            <a href={settings.nocobaseUrl} target="_blank" rel="noreferrer">
              Open NocoBase →
            </a>
          )}
        </div>

        <div className="card">
          <h2>Tailscale SSH (ops)</h2>
          <p style={{ color: "var(--tex-muted)", fontSize: "0.9rem" }}>
            Private path to the host without opening public ports. Install
            Tailscale on the server, then SSH via MagicDNS name.
          </p>
          <div className="field">
            <label htmlFor="ts">Hostname</label>
            <input
              id="ts"
              value={settings.tailscaleHostname}
              onChange={(e) =>
                setSettings({ tailscaleHostname: e.target.value })
              }
              placeholder="tex-host.tailnet-name.ts.net"
            />
          </div>
          {settings.tailscaleHostname && (
            <p className="mono">
              ssh {settings.tailscaleHostname}
            </p>
          )}
          <p style={{ fontSize: "0.85rem", color: "var(--tex-muted)" }}>
            Docs:{" "}
            <a
              href="https://tailscale.com/kb/1193/tailscale-ssh"
              target="_blank"
              rel="noreferrer"
            >
              Tailscale SSH
            </a>
          </p>
        </div>
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <h2>Onboarding & data</h2>
        <div className="btn-row">
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => setSettings({ onboarded: false })}
          >
            Replay onboarding
          </button>
          <Link className="btn btn-ghost" to="/onboarding">
            Open onboarding
          </Link>
          <button className="btn btn-ghost" type="button" onClick={resetSettings}>
            Reset settings
          </button>
        </div>
        <p style={{ color: "var(--tex-muted)", fontSize: "0.85rem" }}>
          Run installer:{" "}
          <span className="mono">bash scripts/install/install.sh</span>
        </p>
      </div>
    </div>
  );
}
