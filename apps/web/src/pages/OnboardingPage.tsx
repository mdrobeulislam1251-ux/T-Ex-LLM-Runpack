import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { health } from "../lib/api";
import { useBrand } from "../state/brand";
import { useSettings } from "../state/settings";

function Stage({ title, body }: { title: string; body: string }) {
  return (
    <div className="stage-wrap" aria-hidden={false}>
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
      lede="Hyper-agentic SaaS console: durable paths, team runners, and sellable agent firmware."
    >
      <Stage
        title="Multi-agent control plane"
        body="Plan · Execute · Review · Integrate"
      />
      <div className="btn-row">
        <button
          className="btn btn-primary"
          type="button"
          onClick={() => nav("/onboarding/agents")}
        >
          Continue
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

function Agents() {
  const nav = useNavigate();
  return (
    <StepShell
      title="Team runners"
      lede="Accuracy comes from roles with allowlisted tools and explicit handoffs—not one giant chat."
    >
      <div className="grid-2">
        {["Planner", "Executor", "Reviewer", "Integrator"].map((r) => (
          <div className="card" key={r}>
            <h2>{r}</h2>
            <p style={{ margin: 0, color: "var(--tex-muted)" }}>
              Narrow responsibility, structured JSON handoffs, budget limits.
            </p>
          </div>
        ))}
      </div>
      <div className="btn-row">
        <button className="btn btn-ghost" type="button" onClick={() => nav(-1)}>
          Back
        </button>
        <button
          className="btn btn-primary"
          type="button"
          onClick={() => nav("/onboarding/brand")}
        >
          Continue
        </button>
      </div>
    </StepShell>
  );
}

function BrandStep() {
  const nav = useNavigate();
  const { brand, setBrand } = useBrand();
  return (
    <StepShell
      title="Brand your console"
      lede="Live tokens apply immediately. Full controls live under Brand anytime."
    >
      <div className="card">
        <div className="field">
          <label htmlFor="logo">Product name</label>
          <input
            id="logo"
            value={brand.logoText}
            onChange={(e) => setBrand({ logoText: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="primary">Primary</label>
          <input
            id="primary"
            type="color"
            value={brand.primary}
            onChange={(e) => setBrand({ primary: e.target.value })}
          />
        </div>
      </div>
      <div className="btn-row">
        <button className="btn btn-ghost" type="button" onClick={() => nav(-1)}>
          Back
        </button>
        <button
          className="btn btn-primary"
          type="button"
          onClick={() => nav("/onboarding/connect")}
        >
          Continue
        </button>
      </div>
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
      lede="Leave Host URL empty to use the Vite proxy (localhost:8080). Set API key to match HOST_API_KEY."
    >
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
        Prefer Open Design–style local CLIs? Point Grok/Claude/Codex at this repo
        playbooks while the host runs jobs in parallel. See{" "}
        <Link to="/settings">Settings</Link>.
      </p>
    </StepShell>
  );
}

export function OnboardingPage() {
  return (
    <Routes>
      <Route index element={<Welcome />} />
      <Route path="agents" element={<Agents />} />
      <Route path="brand" element={<BrandStep />} />
      <Route path="connect" element={<Connect />} />
      <Route path="*" element={<Navigate to="/onboarding" replace />} />
    </Routes>
  );
}
