const BRAINS = [
  {
    id: "planner",
    name: "Planner brain",
    desc: "Decomposes goals into steps + success criteria",
    tier: "cheap",
  },
  {
    id: "executor",
    name: "Executor brain",
    desc: "Produces drafts with allowlisted tools",
    tier: "default",
  },
  {
    id: "reviewer",
    name: "Reviewer brain",
    desc: "Verifies criteria; triggers rework loops",
    tier: "cheap",
  },
  {
    id: "integrator",
    name: "Integrator brain",
    desc: "Packages API-ready payloads",
    tier: "cheap",
  },
];

export function BrainsPage() {
  return (
    <div>
      <h1>Brains</h1>
      <p className="lede">
        Role-level model policies for team runners. Wire model IDs in Settings /
        env later.
      </p>
      <div className="grid-2">
        {BRAINS.map((b) => (
          <div key={b.id} className="card">
            <h2>{b.name}</h2>
            <p className="empty-hint">{b.desc}</p>
            <span className="chip run">tier: {b.tier}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
