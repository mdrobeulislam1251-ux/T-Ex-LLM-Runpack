export function MCPPage() {
  return (
    <div>
      <h1>MCP</h1>
      <p className="lede">
        Model Context Protocol endpoints for tools the console and host can
        expose. Scaffold for upcoming host MCP gateway.
      </p>
      <div className="grid-2">
        <div className="card">
          <h2>Planned servers</h2>
          <ul>
            <li>
              <strong>tex-jobs</strong> — create/poll jobs
            </li>
            <li>
              <strong>tex-firmware</strong> — list/load packages
            </li>
            <li>
              <strong>tex-memory</strong> — read/write memory keys
            </li>
          </ul>
        </div>
        <div className="card">
          <h2>Client config (preview)</h2>
          <pre className="mono" style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {`{
  "mcpServers": {
    "texllm": {
      "url": "http://127.0.0.1:8080/mcp"
    }
  }
}`}
          </pre>
          <p className="empty-hint" style={{ marginTop: "0.75rem" }}>
            Endpoint not live yet — track in host roadmap.
          </p>
        </div>
      </div>
    </div>
  );
}
