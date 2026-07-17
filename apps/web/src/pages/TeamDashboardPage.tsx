import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  addKanbanCard,
  exportTeamFirmware,
  moveKanbanCard,
  runTeam,
  teamDashboard,
  updateKpi,
  type KanbanCard,
  type Kpi,
} from "../lib/workspace";
import { useSettings } from "../state/settings";

function trendIcon(t: string) {
  if (t === "up") return "↑";
  if (t === "down") return "↓";
  return "→";
}

export function TeamDashboardPage() {
  const { slug = "" } = useParams();
  const { settings } = useSettings();
  const [data, setData] = useState<Awaited<ReturnType<typeof teamDashboard>> | null>(
    null
  );
  const [goal, setGoal] = useState("");
  const [cardTitle, setCardTitle] = useState("");
  const [runOut, setRunOut] = useState<string | null>(null);
  const [exportOut, setExportOut] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setData(await teamDashboard(settings, slug));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [settings, slug]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function onRun(e: FormEvent) {
    e.preventDefault();
    if (!goal.trim()) return;
    setBusy(true);
    setRunOut(null);
    try {
      const r = await runTeam(settings, slug, goal.trim());
      setRunOut(JSON.stringify(r, null, 2));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onExport() {
    setExporting(true);
    setExportOut(null);
    try {
      const r = await exportTeamFirmware(settings, slug);
      setExportOut(
        `Exported ${r.package_id}@${r.version} → ${r.path} (${r.brains_exported} brains, ${r.skills_exported} skills)`
      );
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  }

  async function onAddCard(e: FormEvent) {
    e.preventDefault();
    if (!cardTitle.trim()) return;
    await addKanbanCard(settings, slug, {
      title: cardTitle.trim(),
      column_key: "todo",
    });
    setCardTitle("");
    await refresh();
  }

  async function onMove(card: KanbanCard, column_key: string) {
    await moveKanbanCard(settings, card.id, column_key);
    await refresh();
  }

  async function bumpKpi(k: Kpi, delta: number) {
    const n = Number(k.value);
    if (Number.isNaN(n)) return;
    await updateKpi(settings, k.id, { value: String(n + delta) });
    await refresh();
  }

  if (error && !data) {
    return (
      <div>
        <Link to="/workspace">← Workspace</Link>
        <div className="status-banner error">{error}</div>
      </div>
    );
  }

  if (!data) return <p className="pulse">Loading team…</p>;

  const t = data.team;
  const stats = data.stats || {
    brains: 0,
    skills: 0,
    ideas: 0,
    open_cards: 0,
    done_cards: 0,
    activities: 0,
  };
  const columns = data.kanban?.columns || [];
  const kpis = data.kpis || [];

  return (
    <div>
      <p>
        <Link to="/workspace">← Workspace</Link>
      </p>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          gap: "0.75rem",
          alignItems: "flex-start",
        }}
      >
        <div>
          <h1 style={{ borderLeft: `4px solid ${t.color}`, paddingLeft: "0.65rem" }}>
            {t.name}
          </h1>
          <p className="lede">
            {t.description} ·{" "}
            <span className="mono">tex run {t.slug} "…"</span> ·{" "}
            <span className="mono">@{t.slug}</span>
          </p>
        </div>
        <div className="btn-row" style={{ marginTop: 0 }}>
          <button
            type="button"
            className="btn btn-primary"
            disabled={exporting}
            onClick={() => void onExport()}
          >
            {exporting ? "Exporting…" : "Export brains → firmware"}
          </button>
        </div>
      </div>

      {exportOut && (
        <div className="status-banner ok" style={{ marginBottom: "1rem" }}>
          {exportOut}
        </div>
      )}
      {error && (
        <div className="status-banner error" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {/* KPI strip */}
      <div className="kpi-grid">
        {kpis.map((k) => (
          <div key={k.id} className="kpi-card">
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">
              {k.value}
              {k.unit ? <span className="kpi-unit">{k.unit}</span> : null}
              <span className={"kpi-trend trend-" + (k.trend || "flat")}>
                {trendIcon(k.trend)}
              </span>
            </div>
            <div className="btn-row" style={{ marginTop: "0.4rem" }}>
              <button
                type="button"
                className="btn btn-sm btn-ghost"
                onClick={() => void bumpKpi(k, 1)}
              >
                +
              </button>
              <button
                type="button"
                className="btn btn-sm btn-ghost"
                onClick={() => void bumpKpi(k, -1)}
              >
                −
              </button>
            </div>
          </div>
        ))}
        <div className="kpi-card">
          <div className="kpi-label">Brains</div>
          <div className="kpi-value">{stats.brains}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Open cards</div>
          <div className="kpi-value">{stats.open_cards}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Skills</div>
          <div className="kpi-value">{stats.skills}</div>
        </div>
      </div>

      {/* Kanban */}
      <h2 style={{ marginTop: "1.25rem" }}>Agentic flow board</h2>
      <form className="card" onSubmit={onAddCard} style={{ marginBottom: "0.75rem" }}>
        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor="card">New card</label>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <input
              id="card"
              style={{ flex: 1, minWidth: 180 }}
              value={cardTitle}
              onChange={(e) => setCardTitle(e.target.value)}
              placeholder="Work item for this team"
            />
            <button type="submit" className="btn btn-primary btn-sm">
              Add to To do
            </button>
          </div>
        </div>
      </form>

      <div className="kanban">
        {columns.map((col) => (
          <div key={col.key} className="kanban-col">
            <div className="kanban-col-head">
              {col.label}
              <span className="chip">{col.cards?.length || 0}</span>
            </div>
            <div className="kanban-col-body">
              {(col.cards || []).map((card) => (
                <div key={card.id} className="kanban-card">
                  <strong>{card.title}</strong>
                  {card.detail && (
                    <p className="empty-hint" style={{ margin: "0.25rem 0 0" }}>
                      {card.detail}
                    </p>
                  )}
                  <div className="kanban-card-meta">
                    <span className={"chip pri-" + card.priority}>{card.priority}</span>
                    <select
                      aria-label={`Move ${card.title}`}
                      value={card.column_key}
                      onChange={(e) => void onMove(card, e.target.value)}
                    >
                      {columns.map((c) => (
                        <option key={c.key} value={c.key}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <form className="card" onSubmit={onRun} style={{ marginTop: "1.25rem" }}>
        <h2>Run team agentic flow</h2>
        <p className="empty-hint">
          Uses exported firmware <span className="mono">{t.slug}-agents</span> if
          present, else sample-assistant. Claude-first auth from Settings.
        </p>
        <div className="field">
          <label htmlFor="goal">Goal</label>
          <textarea
            id="goal"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder={`What should ${t.name} agents deliver?`}
            required
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Running…" : "Run agentic flow"}
        </button>
      </form>

      {runOut && (
        <pre className="card mono" style={{ marginTop: "1rem", whiteSpace: "pre-wrap" }}>
          {runOut}
        </pre>
      )}

      <div className="grid-2" style={{ marginTop: "1rem" }}>
        <div className="card">
          <h2>Brains</h2>
          <ul>
            {data.brains.map((b) => (
              <li key={b.id}>
                <strong>{b.name}</strong>{" "}
                <span className="chip">{b.role}</span>
                <div className="empty-hint">{b.prompt?.slice(0, 140)}</div>
              </li>
            ))}
            {!data.brains.length && <p className="empty-hint">No brains yet</p>}
          </ul>
        </div>
        <div className="card">
          <h2>Skills</h2>
          <ul>
            {data.skills.map((s) => (
              <li key={s.id}>
                <strong>{s.name}</strong>
                <div className="empty-hint">{s.description}</div>
              </li>
            ))}
            {!data.skills.length && <p className="empty-hint">No skills yet</p>}
          </ul>
        </div>
        <div className="card">
          <h2>Ideas</h2>
          <ul>
            {data.ideas.map((i, idx) => (
              <li key={idx}>
                <strong>{i.title}</strong>
                <div className="empty-hint">{i.summary}</div>
              </li>
            ))}
            {!data.ideas.length && (
              <p className="empty-hint">
                None yet — <Link to="/domain-review">domain review</Link>
              </p>
            )}
          </ul>
        </div>
        <div className="card">
          <h2>Activity</h2>
          <ul className="timeline">
            {data.activities.map((a, i) => (
              <li key={i}>
                <strong>{a.title}</strong>
                <div className="empty-hint">{a.detail}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
