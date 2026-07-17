"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { DashboardData, TeamInfo, CompanyInfo } from "@/lib/data";

/* ── Team accent colors ─────────────────────────────────────────── */

const TEAM_ACCENTS: Record<string, { text: string; border: string; bg: string }> = {
  executive: { text: "text-neon-amber", border: "border-neon-amber/30", bg: "bg-neon-amber/10" },
  engineering: { text: "text-neon-cyan", border: "border-neon-cyan/30", bg: "bg-neon-cyan/10" },
  design: { text: "text-neon-magenta", border: "border-neon-magenta/30", bg: "bg-neon-magenta/10" },
  ai: { text: "text-neon-violet", border: "border-neon-violet/30", bg: "bg-neon-violet/10" },
  "issue-fixers": { text: "text-neon-rose", border: "border-neon-rose/30", bg: "bg-neon-rose/10" },
  technical: { text: "text-neon-blue", border: "border-neon-blue/30", bg: "bg-neon-blue/10" },
  marketing: { text: "text-neon-orange", border: "border-neon-orange/30", bg: "bg-neon-orange/10" },
  sales: { text: "text-neon-lime", border: "border-neon-lime/30", bg: "bg-neon-lime/10" },
  research: { text: "text-neon-teal", border: "border-neon-teal/30", bg: "bg-neon-teal/10" },
};

const NAV = [
  { id: "overview", label: "Overview", icon: "◈" },
  { id: "teams", label: "Teams", icon: "⬡" },
  { id: "brain", label: "Brain Studio", icon: "✦" },
  { id: "companies", label: "Companies", icon: "▣" },
  { id: "logs", label: "Gates & Logs", icon: "≡" },
] as const;

type NavId = (typeof NAV)[number]["id"];

/* ── Animated counter ───────────────────────────────────────────── */

function CountUp({ value }: { value: number }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    if (value === 0) return setDisplay(0);
    let frame = 0;
    const steps = 30;
    const timer = setInterval(() => {
      frame += 1;
      setDisplay(Math.round(value * (1 - Math.pow(1 - frame / steps, 3))));
      if (frame >= steps) clearInterval(timer);
    }, 24);
    return () => clearInterval(timer);
  }, [value]);
  return <span>{display}</span>;
}

/* ── Shell ──────────────────────────────────────────────────────── */

export function CommandDeck({ data }: { data: DashboardData }) {
  const [tab, setTab] = useState<NavId>("overview");
  const active = data.companies.find((c) => c.slug === data.activeSlug) ?? null;

  return (
    <div className="mx-auto flex min-h-screen max-w-[1400px] gap-6 px-6 py-6">
      {/* Sidebar */}
      <aside className="glass sticky top-6 hidden h-[calc(100vh-3rem)] w-60 shrink-0 flex-col p-5 md:flex">
        <div className="mb-1 flex items-center gap-2.5">
          <div className="neon-ring flex h-9 w-9 items-center justify-center rounded-xl bg-neon-cyan/10 font-mono text-lg text-neon-cyan">
            A
          </div>
          <div>
            <div className="text-sm font-700 font-bold tracking-wide text-white">ARION</div>
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">Command Deck</div>
          </div>
        </div>
        <div className="shimmer-line my-4" />
        <nav className="flex flex-col gap-1">
          {NAV.map((item) => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-all ${
                tab === item.id
                  ? "bg-neon-cyan/10 text-neon-cyan shadow-[inset_0_0_0_1px_rgba(34,211,238,0.25)]"
                  : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
              }`}
            >
              <span className="font-mono">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>
        <div className="mt-auto">
          <div className="glass rounded-xl border-line p-3.5">
            <div className="mb-1.5 flex items-center gap-2">
              <span className={`status-dot ${active ? "live" : "bg-slate-600"}`} />
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-400">Active Brain</span>
            </div>
            <div className="truncate text-sm font-semibold text-white">{active ? active.name : "None"}</div>
            <div className="truncate font-mono text-[11px] text-slate-500">
              {active ? `companies/${active.slug}` : "run Brain Studio →"}
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="min-w-0 flex-1">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="glow-text text-2xl font-bold tracking-tight text-white">
              {NAV.find((n) => n.id === tab)?.label}
            </h1>
            <p className="mt-0.5 text-sm text-slate-400">
              {tab === "overview" && "Live state of your agent company"}
              {tab === "teams" && `${data.agentCount} specialists across ${data.teams.length} teams`}
              {tab === "brain" && "Generate a company brain from nothing but your vision"}
              {tab === "companies" && "Every brain in this repo — one is live at a time"}
              {tab === "logs" && "CTO decisions and incident history for the active company"}
            </p>
          </div>
          <div className="glass flex items-center gap-2 rounded-full px-4 py-2">
            <span className="status-dot live" />
            <span className="font-mono text-xs text-slate-300">52 agents · 9 teams</span>
          </div>
        </header>

        {tab === "overview" && <Overview data={data} active={active} onNavigate={setTab} />}
        {tab === "teams" && <Teams teams={data.teams} />}
        {tab === "brain" && <BrainStudio />}
        {tab === "companies" && <Companies companies={data.companies} activeSlug={data.activeSlug} />}
        {tab === "logs" && <Logs decisions={data.decisions} incidents={data.incidents} active={active} />}
      </main>
    </div>
  );
}

/* ── Overview ───────────────────────────────────────────────────── */

function Overview({
  data,
  active,
  onNavigate,
}: {
  data: DashboardData;
  active: CompanyInfo | null;
  onNavigate: (t: NavId) => void;
}) {
  const stats = [
    { label: "Agents", value: data.agentCount, accent: "text-neon-cyan" },
    { label: "Teams", value: data.teams.length, accent: "text-neon-violet" },
    { label: "Skills", value: data.skillCount, accent: "text-neon-magenta" },
    { label: "Commands", value: data.commandCount, accent: "text-neon-lime" },
    { label: "Companies", value: data.companies.length, accent: "text-neon-amber" },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {stats.map((s, i) => (
          <div
            key={s.label}
            className="glass glass-hover scan-card animate-fade-up p-5"
            style={{ animationDelay: `${i * 70}ms` }}
          >
            <div className={`font-mono text-3xl font-semibold ${s.accent}`}>
              <CountUp value={s.value} />
            </div>
            <div className="mt-1 font-mono text-[11px] uppercase tracking-[0.18em] text-slate-400">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Active brain card */}
        <div className="glass scan-card animate-fade-up p-6 lg:col-span-3" style={{ animationDelay: "250ms" }}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-300">Active Company Brain</h2>
            <span className={`status-dot ${active ? "live" : "bg-slate-600"}`} />
          </div>
          {active ? (
            <div className="space-y-4">
              <div>
                <div className="text-xl font-bold text-white">{active.name}</div>
                {active.appName && <div className="font-mono text-sm text-neon-cyan">{active.appName}</div>}
                <p className="mt-2 text-sm leading-relaxed text-slate-300">{active.description || "—"}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <BrainField label="Vision" value={active.vision} />
                <BrainField label="Emotion / Tone" value={active.emotionTone} />
                <BrainField label="Scope — does" value={active.scopeDoes} />
                <BrainField label="Audience" value={active.targetAudience} />
              </div>
              {active.status === "draft" && (
                <div className="rounded-lg border border-neon-amber/30 bg-neon-amber/10 px-4 py-3 text-sm text-neon-amber">
                  Brain pending research generation — run{" "}
                  <code className="font-mono">/onboard {active.name}</code> in Claude Code to let the research team
                  complete it.
                </div>
              )}
            </div>
          ) : (
            <div className="py-8 text-center">
              <div className="animate-float-y mb-3 font-mono text-4xl text-neon-cyan/60">✦</div>
              <p className="text-sm text-slate-400">No company brain is active yet.</p>
              <button
                onClick={() => onNavigate("brain")}
                className="mt-4 rounded-lg border border-neon-cyan/40 bg-neon-cyan/10 px-5 py-2.5 text-sm font-semibold text-neon-cyan transition-all hover:bg-neon-cyan/20 hover:shadow-[0_0_24px_-4px_rgba(34,211,238,0.5)]"
              >
                Generate one in Brain Studio →
              </button>
            </div>
          )}
        </div>

        {/* Pipeline gates card */}
        <div className="glass animate-fade-up p-6 lg:col-span-2" style={{ animationDelay: "320ms" }}>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-[0.16em] text-slate-300">Hard Review Gates</h2>
          <ul className="space-y-3">
            {[
              ["Data schemas", "cto", "engineering"],
              ["Architecture", "cto", "engineering"],
              ["Design output", "design-director", "design"],
              ["UI fidelity", "design-system-engineer", "design"],
              ["AI features", "ai-eval-engineer", "ai"],
              ["Bug fixes", "regression-tester", "issue-fixers"],
            ].map(([what, who, team]) => (
              <li key={what as string} className="flex items-center justify-between gap-2 text-sm">
                <span className="text-slate-300">{what}</span>
                <span
                  className={`rounded-full border px-2.5 py-0.5 font-mono text-[11px] ${TEAM_ACCENTS[team as string].text} ${TEAM_ACCENTS[team as string].border} ${TEAM_ACCENTS[team as string].bg}`}
                >
                  {who}
                </span>
              </li>
            ))}
          </ul>
          <div className="shimmer-line my-4" />
          <p className="font-mono text-[11px] leading-relaxed text-slate-500">
            Gates are enforced in Claude Code by the orchestration-runpack skill. Nothing ships ungated.
          </p>
        </div>
      </div>
    </div>
  );
}

function BrainField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-black/20 p-3">
      <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="text-sm text-slate-200">{value || <span className="text-slate-600">not set</span>}</div>
    </div>
  );
}

/* ── Teams ──────────────────────────────────────────────────────── */

function Teams({ teams }: { teams: TeamInfo[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  return (
    <div className="space-y-4">
      {teams.map((team, i) => {
        const accent = TEAM_ACCENTS[team.id] ?? TEAM_ACCENTS.engineering;
        const open = expanded === team.id;
        return (
          <div key={team.id} className="glass animate-fade-up overflow-hidden" style={{ animationDelay: `${i * 60}ms` }}>
            <button
              onClick={() => setExpanded(open ? null : team.id)}
              className="scan-card flex w-full items-center justify-between px-6 py-4 text-left"
            >
              <div className="flex items-center gap-4">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-xl border font-mono text-sm ${accent.text} ${accent.border} ${accent.bg}`}
                >
                  {team.agents.length}
                </div>
                <div>
                  <div className="font-semibold text-white">{team.label}</div>
                  <div className="font-mono text-[11px] text-slate-500">
                    {team.agents.map((a) => a.name).join(" · ")}
                  </div>
                </div>
              </div>
              <span className={`font-mono text-lg transition-transform ${open ? "rotate-90" : ""} ${accent.text}`}>
                ›
              </span>
            </button>
            {open && (
              <div className="grid gap-3 border-t border-line px-6 py-5 sm:grid-cols-2">
                {team.agents.map((agent) => (
                  <div key={agent.name} className={`glass-hover rounded-xl border p-4 ${accent.border} bg-black/20`}>
                    <div className={`font-mono text-sm font-semibold ${accent.text}`}>{agent.name}</div>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-slate-400">{agent.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Brain Studio ───────────────────────────────────────────────── */

function BrainStudio() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [briefing, setBriefing] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  async function generate() {
    setBusy(true);
    setResult(null);
    try {
      const res = await fetch("/api/brain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, briefing }),
      });
      const json = await res.json();
      setResult(res.ok ? { ok: true, message: json.next_step } : { ok: false, message: json.error });
      if (res.ok) {
        setName("");
        setBriefing("");
        router.refresh();
      }
    } catch {
      setResult({ ok: false, message: "Request failed — is the dashboard running inside the Arion repo?" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="glass scan-card animate-fade-up p-6 lg:col-span-3">
        <h2 className="mb-1 text-lg font-bold text-white">You bring the vision. Arion builds the brain.</h2>
        <p className="mb-6 text-sm leading-relaxed text-slate-400">
          Don&apos;t fill in scope documents or tone guides — just say what you know about the company and where it
          should go. The research team (research-lead, market-analyst, product-strategist) generates the full brain.
        </p>
        <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-[0.18em] text-slate-400">
          Company name
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Outboundrix"
          className="mb-5 w-full rounded-lg border border-line bg-black/30 px-4 py-3 text-sm text-white outline-none transition-all placeholder:text-slate-600 focus:border-neon-cyan/50 focus:shadow-[0_0_20px_-6px_rgba(34,211,238,0.4)]"
        />
        <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-[0.18em] text-slate-400">
          Company structure &amp; vision — in your own words
        </label>
        <textarea
          value={briefing}
          onChange={(e) => setBriefing(e.target.value)}
          rows={7}
          placeholder="What does the company do? Who is it for? Where do you want it to be in 2 years? Anything about how it should feel..."
          className="mb-5 w-full resize-y rounded-lg border border-line bg-black/30 px-4 py-3 text-sm leading-relaxed text-white outline-none transition-all placeholder:text-slate-600 focus:border-neon-violet/50 focus:shadow-[0_0_20px_-6px_rgba(139,92,246,0.4)]"
        />
        <button
          onClick={generate}
          disabled={busy}
          className="w-full rounded-lg border border-neon-cyan/40 bg-gradient-to-r from-neon-cyan/15 to-neon-violet/15 px-6 py-3.5 text-sm font-bold tracking-wide text-neon-cyan transition-all hover:from-neon-cyan/25 hover:to-neon-violet/25 hover:shadow-[0_0_32px_-6px_rgba(34,211,238,0.5)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Creating brain request…" : "✦ Generate Company Brain"}
        </button>
        {result && (
          <div
            className={`mt-4 rounded-lg border px-4 py-3 text-sm ${
              result.ok
                ? "border-neon-lime/30 bg-neon-lime/10 text-neon-lime"
                : "border-neon-rose/30 bg-neon-rose/10 text-neon-rose"
            }`}
          >
            {result.message}
          </div>
        )}
      </div>

      <div className="glass animate-fade-up p-6 lg:col-span-2" style={{ animationDelay: "120ms" }}>
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.16em] text-slate-300">How generation works</h3>
        <ol className="space-y-4">
          {[
            ["01", "You describe", "Name + whatever you know about structure and vision. That's all."],
            ["02", "Research team sweeps", "research-lead frames it, market-analyst maps the market, product-strategist derives scope, mission and differentiation."],
            ["03", "Brain is drafted", "Scope, vision, mission, emotion/tone, audience and voice examples — generated, not asked."],
            ["04", "One confirm pass", "You approve or adjust the generated brain in Claude Code (/onboard picks up the request automatically)."],
            ["05", "Only real secrets asked", "DB and n8n credentials go to .env; brand files get uploaded. These can't be researched — everything else is."],
          ].map(([num, title, desc]) => (
            <li key={num} className="flex gap-3">
              <span className="font-mono text-xs text-neon-violet">{num}</span>
              <div>
                <div className="text-sm font-semibold text-slate-200">{title}</div>
                <div className="mt-0.5 text-[13px] leading-relaxed text-slate-500">{desc}</div>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

/* ── Companies ──────────────────────────────────────────────────── */

function Companies({ companies, activeSlug }: { companies: CompanyInfo[]; activeSlug: string | null }) {
  const router = useRouter();
  const [busySlug, setBusySlug] = useState<string | null>(null);

  async function activate(slug: string) {
    setBusySlug(slug);
    try {
      await fetch("/api/active", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug }),
      });
      router.refresh();
    } finally {
      setBusySlug(null);
    }
  }

  if (companies.length === 0) {
    return (
      <div className="glass animate-fade-up p-10 text-center">
        <div className="animate-float-y mb-3 font-mono text-4xl text-neon-violet/60">▣</div>
        <p className="text-sm text-slate-400">
          No company brains yet. Create the first one in <span className="text-neon-cyan">Brain Studio</span>.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {companies.map((company, i) => {
        const isActive = company.slug === activeSlug;
        return (
          <div
            key={company.slug}
            className={`glass glass-hover scan-card animate-fade-up p-5 ${isActive ? "neon-ring" : ""}`}
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="mb-3 flex items-start justify-between gap-2">
              <div>
                <div className="text-lg font-bold text-white">{company.name}</div>
                <div className="font-mono text-[11px] text-slate-500">companies/{company.slug}</div>
              </div>
              {isActive ? (
                <span className="flex items-center gap-1.5 rounded-full border border-neon-cyan/40 bg-neon-cyan/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-neon-cyan">
                  <span className="status-dot live" /> live
                </span>
              ) : (
                <button
                  onClick={() => activate(company.slug)}
                  disabled={busySlug !== null}
                  className="rounded-full border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-slate-400 transition-all hover:border-neon-cyan/40 hover:text-neon-cyan disabled:opacity-50"
                >
                  {busySlug === company.slug ? "…" : "activate"}
                </button>
              )}
            </div>
            <p className="mb-3 line-clamp-2 text-[13px] leading-relaxed text-slate-400">
              {company.description || "No description"}
            </p>
            <div className="flex flex-wrap gap-2">
              <Badge ok={company.status === "complete"} label={company.status === "complete" ? "brain complete" : company.status === "draft" ? "research pending" : "profile invalid"} />
              <Badge ok={company.hasCredentials} label={company.hasCredentials ? "credentials wired" : "credentials pending"} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`rounded-full border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${
        ok ? "border-neon-lime/30 bg-neon-lime/10 text-neon-lime" : "border-neon-amber/30 bg-neon-amber/10 text-neon-amber"
      }`}
    >
      {label}
    </span>
  );
}

/* ── Logs ───────────────────────────────────────────────────────── */

function Logs({ decisions, incidents, active }: { decisions: string; incidents: string; active: CompanyInfo | null }) {
  const panels = useMemo(
    () => [
      { title: "CTO Decision Log", body: decisions, accent: "text-neon-amber", hint: "Schema & architecture verdicts land here (decisions.md)" },
      { title: "Incident & Pattern Log", body: incidents, accent: "text-neon-rose", hint: "Postmortems and failure classes land here (incidents.md)" },
    ],
    [decisions, incidents]
  );

  if (!active) {
    return (
      <div className="glass animate-fade-up p-10 text-center">
        <p className="text-sm text-slate-400">Activate a company to see its decision and incident logs.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {panels.map((panel, i) => (
        <div key={panel.title} className="glass animate-fade-up p-6" style={{ animationDelay: `${i * 100}ms` }}>
          <h2 className={`mb-1 text-sm font-semibold uppercase tracking-[0.16em] ${panel.accent}`}>{panel.title}</h2>
          <p className="mb-4 font-mono text-[11px] text-slate-500">{panel.hint}</p>
          <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg border border-line bg-black/30 p-4 font-mono text-xs leading-relaxed text-slate-300">
            {panel.body.trim() || "— empty —"}
          </pre>
        </div>
      ))}
    </div>
  );
}
