import { FormEvent, useEffect, useRef, useState, type ReactNode } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { FriendlyAgentOnboard } from "../components/FriendlyAgentOnboard";
import {
  health,
  loadBackendConfigLocal,
  saveBackendConfigLocal,
} from "../lib/api";
import { useBrand } from "../state/brand";
import { useSettings, type DbMode } from "../state/settings";
import { useTaskStore } from "../state/task";
import { THEME_OPTIONS, useTheme, type ThemeId } from "../state/theme";

function Stage({ title, body }: { title: string; body: string }) {
  return (
    <div className="stage-wrap">
      <div className="stage-3d" aria-hidden>
        <div className="stage-card back">
          <span style={{ color: "var(--tex-muted)" }}>Team runner layer</span>
        </div>
        <div className="stage-card front">
          <div>
            <strong>{title}</strong>
            <p style={{ margin: "0.4rem 0 0", color: "var(--tex-muted)" }}>
              {body}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function StepShell({
  title,
  lede,
  children,
}: {
  title: string;
  lede: string;
  children: ReactNode;
}) {
  const hRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    hRef.current?.focus();
  }, [title]);
  return (
    <div>
      <h1 ref={hRef} tabIndex={-1}>
        {title}
      </h1>
      <p className="lede">{lede}</p>
      {children}
    </div>
  );
}

function Welcome() {
  const nav = useNavigate();
  const { setSettings } = useSettings();
  return (
    <StepShell
      title="Welcome to T-ex LLM"
      lede="A friendly hyper-agentic workspace — we will set up your backend, brand, and first tasks together."
    >
      <FriendlyAgentOnboard
        title="Hi, I'm Tex 👋"
        message="I'll guide you through database choice, company identity, theme, and connecting the agent host. You can skip anytime."
      />
      <Stage
        title="Multi-agent control plane"
        body="Plan · Execute · Review · Integrate"
      />
      <div className="btn-row">
        <button
          className="btn btn-primary"
          type="button"
          onClick={() => nav("/onboarding/backend")}
        >
          Start setup
        </button>
        <button
          className="btn btn-ghost"
          type="button"
          onClick={() => {
            setSettings({ onboarded: true });
            nav("/jobs");
          }}
        >
          Skip onboarding
        </button>
      </div>
    </StepShell>
  );
}

function BackendConfig() {
  const nav = useNavigate();
  const { setSettings } = useSettings();
  const { setTheme } = useTheme();
  const { setBrand } = useBrand();
  const { addTask, updateTask, tasks } = useTaskStore();
  const existing = loadBackendConfigLocal();

  const [db, setDb] = useState<"postgres" | "supabase" | "other" | "none">(
    existing?.db || "postgres"
  );
  const [port, setPort] = useState(existing?.port || "5432");
  const [domain, setDomain] = useState(existing?.domain || "");
  const [company, setCompany] = useState(existing?.company || "");
  const [vision, setVision] = useState(existing?.vision || "");
  const [themePick, setThemePick] = useState(
    existing?.theme || "minimal-light"
  );

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const payload = {
      db: db as "postgres" | "supabase" | "other" | "none",
      port,
      domain,
      company,
      vision,
      theme: themePick,
    };
    saveBackendConfigLocal(payload);

    const dbMode: DbMode =
      db === "postgres" ? "postgres" : db === "supabase" ? "supabase" : "none";
    setSettings({ dbMode });
    if (company) setBrand({ logoText: company });
    if (
      themePick === "minimal-light" ||
      themePick === "sky" ||
      themePick === "blue" ||
      themePick === "minimal-dark"
    ) {
      setTheme(themePick as ThemeId);
    }

    const onboardTask = tasks.find((t) =>
      t.title.toLowerCase().includes("onboarding")
    );
    if (onboardTask) {
      updateTask(onboardTask.id, { status: "done" });
    } else {
      addTask({
        userId: "operator",
        projectId: "default",
        title: "Onboarding backend config saved",
        details: `${company || "workspace"} · ${db}`,
        status: "done",
      });
    }

    nav("/onboarding/connect");
  }

  return (
    <StepShell
      title="Backend & identity"
      lede="Tell Tex how you want to run data and what this system is for."
    >
      <FriendlyAgentOnboard
        title="A few friendly questions"
        message="Pick Postgres or Supabase if you know it — or Other. Domain and vision help agents stay on-brand."
      />
      <form className="card" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="db">Database</label>
          <select
            id="db"
            value={db}
            onChange={(e) =>
              setDb(e.target.value as "postgres" | "supabase" | "other" | "none")
            }
          >
            <option value="postgres">Postgres</option>
            <option value="supabase">Supabase</option>
            <option value="other">Other / decide later</option>
            <option value="none">None (in-memory)</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="port">Port</label>
          <input
            id="port"
            value={port}
            onChange={(e) => setPort(e.target.value)}
            placeholder="e.g. 5432"
          />
        </div>
        <div className="field">
          <label htmlFor="domain">Domain identity</label>
          <input
            id="domain"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="app.yourcompany.com"
          />
        </div>
        <div className="field">
          <label htmlFor="company">Company name</label>
          <input
            id="company"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Acme Agents"
          />
        </div>
        <div className="field">
          <label htmlFor="vision">Short system vision</label>
          <textarea
            id="vision"
            value={vision}
            onChange={(e) => setVision(e.target.value)}
            placeholder="What should this agent platform achieve?"
          />
        </div>
        <div className="field">
          <label htmlFor="theme">Theme</label>
          <select
            id="theme"
            value={themePick}
            onChange={(e) => setThemePick(e.target.value)}
          >
            {THEME_OPTIONS.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div className="btn-row">
          <button className="btn btn-ghost" type="button" onClick={() => nav(-1)}>
            Back
          </button>
          <button className="btn btn-primary" type="submit">
            Save config & continue
          </button>
        </div>
      </form>
    </StepShell>
  );
}

function Connect() {
  const nav = useNavigate();
  const { settings, setSettings } = useSettings();
  const [msg, setMsg] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  async function test() {
    setMsg(null);
    try {
      const h = await health(settings);
      setOk(true);
      setMsg(`Connected · host v${h.version}`);
    } catch (e) {
      setOk(false);
      setMsg(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <StepShell
      title="Connect host"
      lede="Leave Host URL empty for Vite proxy → localhost:8080."
    >
      <FriendlyAgentOnboard
        title="Almost there"
        message="I'll talk to the host when you probe health. Mock mode works offline with LLM_PROVIDER=mock."
      />
      <div className="card">
        <div className="field">
          <label htmlFor="host">Host URL (optional)</label>
          <input
            id="host"
            placeholder="http://127.0.0.1:8080"
            value={settings.hostUrl}
            onChange={(e) => setSettings({ hostUrl: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="key">API key</label>
          <input
            id="key"
            value={settings.apiKey}
            onChange={(e) => setSettings({ apiKey: e.target.value })}
          />
        </div>
        <div className="btn-row">
          <button className="btn btn-ghost" type="button" onClick={() => void test()}>
            Test connection
          </button>
        </div>
        {msg && (
          <div
            className={"status-banner " + (ok ? "ok" : "error")}
            style={{ marginTop: "1rem" }}
            role="status"
          >
            {msg}
          </div>
        )}
      </div>
      <div className="btn-row">
        <button className="btn btn-ghost" type="button" onClick={() => nav(-1)}>
          Back
        </button>
        <button
          className="btn btn-primary"
          type="button"
          onClick={() => {
            setSettings({ onboarded: true });
            nav("/jobs");
          }}
        >
          Enter console
        </button>
      </div>
      <p style={{ marginTop: "1rem", color: "var(--tex-muted)" }}>
        Prefer chat? <Link to="/chat">Open friendly agent chat</Link>
      </p>
    </StepShell>
  );
}

export function OnboardingPage() {
  return (
    <Routes>
      <Route index element={<Welcome />} />
      <Route path="backend" element={<BackendConfig />} />
      <Route path="connect" element={<Connect />} />
      {/* legacy paths */}
      <Route path="agents" element={<Navigate to="/onboarding/backend" replace />} />
      <Route path="brand" element={<Navigate to="/onboarding/backend" replace />} />
      <Route path="*" element={<Navigate to="/onboarding" replace />} />
    </Routes>
  );
}
