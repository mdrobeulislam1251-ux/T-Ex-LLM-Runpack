const SKILLS = [
  { name: "agentic-platform", path: "skills/agentic-platform", mode: "ops" },
  { name: "agentic-host", path: "skills/agentic-host", mode: "ops" },
  { name: "agentic-workers", path: "skills/agentic-workers", mode: "ops" },
  { name: "agentic-firmware", path: "skills/agentic-firmware", mode: "product" },
  { name: "saas-console", path: "skills/saas-console", mode: "ui" },
  { name: "saas-onboarding", path: "skills/saas-onboarding", mode: "ui" },
  {
    name: "sample-assistant",
    path: "firmware/sample-assistant",
    mode: "firmware",
  },
];

export function SkillsPage() {
  return (
    <div>
      <h1>Skills</h1>
      <p className="lede">
        Open Design–style skill packs and firmware packages in this monorepo.
        Point Claude / Codex / Grok at these paths.
      </p>
      <div className="card" style={{ overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Path</th>
              <th>Mode</th>
            </tr>
          </thead>
          <tbody>
            {SKILLS.map((s) => (
              <tr key={s.name}>
                <td>
                  <strong>{s.name}</strong>
                </td>
                <td className="mono">{s.path}</td>
                <td>
                  <span className="chip">{s.mode}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
