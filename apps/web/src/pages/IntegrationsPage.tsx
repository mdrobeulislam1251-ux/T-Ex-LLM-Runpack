import { useSettings } from "../state/settings";

const ROWS = [
  {
    name: "T-ex Host API",
    status: "built-in",
    note: "Jobs, firmware, health",
  },
  {
    name: "Postgres",
    status: "detect",
    note: "scripts/install/detect-db.sh",
  },
  {
    name: "Supabase",
    status: "detect",
    note: "SUPABASE_URL + backups",
  },
  {
    name: "NocoBase",
    status: "optional",
    note: "deploy/docker-compose.nocobase.yml",
  },
  {
    name: "Tailscale SSH",
    status: "optional",
    note: "Private ops path",
  },
  {
    name: "OpenAI-compatible LLM",
    status: "env",
    note: "LLM_BASE_URL + LLM_API_KEY",
  },
];

export function IntegrationsPage() {
  const { settings } = useSettings();
  return (
    <div>
      <h1>Integrations</h1>
      <p className="lede">
        Connect data and ops planes. Current DB mode:{" "}
        <strong>{settings.dbMode}</strong>
        {settings.nocobaseUrl ? ` · NocoBase ${settings.nocobaseUrl}` : ""}.
      </p>
      <div className="card" style={{ overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Integration</th>
              <th>Status</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.name}>
                <td>
                  <strong>{r.name}</strong>
                </td>
                <td>
                  <span className="chip">{r.status}</span>
                </td>
                <td className="empty-hint">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
