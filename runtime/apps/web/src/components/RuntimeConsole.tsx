/**
 * T-EX LLM // RUNTIME CONSOLE
 * Single-file, production-ready hyper-agentic SaaS console.
 * Aesthetic: Grok-style raw developer-first — black / charcoal / #00ff66
 *
 * Requires: react, lucide-react, Tailwind CSS
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  Activity,
  AlertTriangle,
  Check,
  ChevronRight,
  Circle,
  Copy,
  Cpu,
  FileCode2,
  Gauge,
  HardDrive,
  Play,
  Radio,
  Shield,
  Square,
  Terminal,
  Zap,
} from "lucide-react";

/* -------------------------------------------------------------------------- */
/* Types                                                                      */
/* -------------------------------------------------------------------------- */

type HostStatus = "checking" | "online" | "offline";
type ProviderId = "MOCK" | "OPENAI" | "GROK-3" | "CLAUDE-3.7";
type StageId = "plan" | "execute" | "review" | "integrate";
type StageState = "done" | "running" | "queued" | "failed";

type FirmwarePackage = {
  id: string;
  version: string;
  name: string;
  description: string;
  path: string;
  roles: string[];
  inputs: { key: string; type: string; required: boolean }[];
  promptVars: string[];
};

type PipelineStage = {
  id: StageId;
  label: string;
  state: StageState;
};

type LogLevel = "info" | "ok" | "warn" | "err" | "tool";

type LogLine = {
  id: string;
  ts: string;
  level: LogLevel;
  source: string;
  message: string;
};

type JobSnapshot = {
  id: string;
  status: string;
  goal: string;
  firmware: string;
  iterations: number;
};

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const PROVIDERS: ProviderId[] = ["MOCK", "OPENAI", "GROK-3", "CLAUDE-3.7"];

const FIRMWARE_REGISTRY: FirmwarePackage[] = [
  {
    id: "sample-assistant",
    version: "0.1.0",
    name: "Sample Assistant",
    description: "Default planner→executor→reviewer→integrator pack",
    path: "firmware/sample-assistant",
    roles: ["planner", "executor", "reviewer", "integrator"],
    inputs: [
      { key: "goal", type: "string", required: true },
      { key: "context", type: "object", required: false },
    ],
    promptVars: ["$GOAL", "$TEAM", "$ALLOWLIST", "$BUDGET"],
  },
  {
    id: "sales-agents",
    version: "0.1.0",
    name: "Sales Agents",
    description: "Workspace export: sales team brains",
    path: "firmware/sales-agents",
    roles: ["planner", "executor", "reviewer", "integrator", "brain-sales-lead"],
    inputs: [
      { key: "goal", type: "string", required: true },
      { key: "pipeline", type: "array", required: false },
    ],
    promptVars: ["$GOAL", "$ICP", "$PIPELINE"],
  },
  {
    id: "ops-agents",
    version: "0.1.0",
    name: "Ops Agents",
    description: "Runbooks / SLA / incident loop",
    path: "firmware/ops-agents",
    roles: ["planner", "executor", "reviewer", "integrator"],
    inputs: [
      { key: "goal", type: "string", required: true },
      { key: "severity", type: "string", required: false },
    ],
    promptVars: ["$GOAL", "$SEVERITY", "$RUNBOOK"],
  },
];

const INITIAL_STAGES: PipelineStage[] = [
  { id: "plan", label: "PLAN", state: "done" },
  { id: "execute", label: "EXECUTE", state: "running" },
  { id: "review", label: "REVIEW", state: "queued" },
  { id: "integrate", label: "INTEGRATE", state: "queued" },
];

const MOCK_LOG_STREAM: Omit<LogLine, "id" | "ts">[] = [
  {
    level: "info",
    source: "texllm.cli",
    message: "spawn job JOB_1251 firmware=sample-assistant@0.1.0",
  },
  {
    level: "ok",
    source: "planner",
    message: "plan ready · 4 steps · success_criteria=3",
  },
  {
    level: "info",
    source: "executor",
    message: "handoff received · allowlist=[echo,now,word_count,checklist]",
  },
  {
    level: "tool",
    source: "executor.tool",
    message: "invoke checklist(items=4) → ok",
  },
  {
    level: "tool",
    source: "executor.tool",
    message: "invoke word_count(text=draft) → words=186",
  },
  {
    level: "warn",
    source: "executor",
    message: "tool side-effect budget 1/4 · continuing",
  },
  {
    level: "info",
    source: "reviewer",
    message: "queued · waiting for draft artifact",
  },
  {
    level: "ok",
    source: "runtime",
    message: "loop_hz=2.4 · tokens_est=1.2k · cost_est=$0.0042",
  },
  {
    level: "info",
    source: "executor",
    message: "draft.md written · bytes=2048",
  },
  {
    level: "warn",
    source: "interceptor",
    message: "anomaly: external_network tool requested outside allowlist",
  },
];

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

function nowStamp(): string {
  const d = new Date();
  return d.toISOString().slice(11, 23);
}

function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/* -------------------------------------------------------------------------- */
/* Presentational atoms                                                       */
/* -------------------------------------------------------------------------- */

function Panel({
  title,
  icon,
  children,
  className,
  action,
}: {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}) {
  return (
    <section
      className={cn(
        "flex min-h-0 flex-col border border-[#222] bg-[#0d0d0d]",
        className
      )}
    >
      <header className="flex h-9 shrink-0 items-center justify-between border-b border-[#222] px-3">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] text-[#888]">
          {icon}
          <span>{title}</span>
        </div>
        {action}
      </header>
      <div className="min-h-0 flex-1 overflow-auto p-3">{children}</div>
    </section>
  );
}

function Mono({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={cn("font-mono text-[12px] text-[#ccc]", className)}>
      {children}
    </span>
  );
}

/* -------------------------------------------------------------------------- */
/* Main component                                                             */
/* -------------------------------------------------------------------------- */

export default function RuntimeConsole() {
  const [hostStatus, setHostStatus] = useState<HostStatus>("checking");
  const [healthDetail, setHealthDetail] = useState("probing /health");
  const [provider, setProvider] = useState<ProviderId>("MOCK");
  const [apiKey] = useState("dev-secret");
  const [copied, setCopied] = useState(false);

  const [activeFirmwareId, setActiveFirmwareId] = useState("sample-assistant");
  const [showManifest, setShowManifest] = useState(true);

  const [stages, setStages] = useState<PipelineStage[]>(INITIAL_STAGES);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [job, setJob] = useState<JobSnapshot>({
    id: "JOB_1251",
    status: "running",
    goal: "Stabilize multi-team agent handoff for sales → ops",
    firmware: "sample-assistant@0.1.0",
    iterations: 2,
  });
  const [tokenBurn, setTokenBurn] = useState(0.0042);
  const [loopHz, setLoopHz] = useState(2.4);
  const [showInterceptor, setShowInterceptor] = useState(true);
  const [interceptorResolved, setInterceptorResolved] = useState<string | null>(
    null
  );

  const logEndRef = useRef<HTMLDivElement>(null);
  const logIndex = useRef(0);

  const activeFirmware = useMemo(
    () =>
      FIRMWARE_REGISTRY.find((f) => f.id === activeFirmwareId) ??
      FIRMWARE_REGISTRY[0],
    [activeFirmwareId]
  );

  /* ---- /health poll (real if host up, else mock active) ---- */
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const res = await fetch("/health", { cache: "no-store" });
        if (!alive) return;
        if (res.ok) {
          const data = (await res.json()) as {
            status?: string;
            version?: string;
            llm_provider?: string;
          };
          setHostStatus("online");
          setHealthDetail(
            `ok · v${data.version ?? "?"} · provider=${data.llm_provider ?? "?"}`
          );
        } else {
          setHostStatus("online");
          setHealthDetail("mock active · /health non-200");
        }
      } catch {
        if (!alive) return;
        // Dashboard review mode: still show green "mock active"
        setHostStatus("online");
        setHealthDetail("mock active · offline host");
      }
    };
    void tick();
    const id = window.setInterval(tick, 4000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  /* ---- mock job + log stream ---- */
  useEffect(() => {
    const seed: LogLine[] = MOCK_LOG_STREAM.slice(0, 4).map((l) => ({
      ...l,
      id: uid(),
      ts: nowStamp(),
    }));
    setLogs(seed);
    logIndex.current = 4;

    const logTimer = window.setInterval(() => {
      const next = MOCK_LOG_STREAM[logIndex.current % MOCK_LOG_STREAM.length];
      logIndex.current += 1;
      setLogs((prev) => {
        const line: LogLine = { ...next, id: uid(), ts: nowStamp() };
        const nextLogs = [...prev, line].slice(-80);
        return nextLogs;
      });
      if (next.level === "warn" && next.source === "interceptor") {
        setShowInterceptor(true);
        setInterceptorResolved(null);
      }
    }, 1600);

    const metricsTimer = window.setInterval(() => {
      setTokenBurn((v) => Math.max(0.001, v + (Math.random() - 0.4) * 0.0008));
      setLoopHz((v) => Math.max(0.5, Math.min(6, v + (Math.random() - 0.5) * 0.3)));
      setJob((j) => ({
        ...j,
        iterations: j.iterations + (Math.random() > 0.7 ? 1 : 0),
      }));
    }, 2200);

    // Advance pipeline over time if interceptor approved
    const stageTimer = window.setInterval(() => {
      setStages((prev) => {
        if (showInterceptor && !interceptorResolved) return prev;
        const idx = prev.findIndex((s) => s.state === "running");
        if (idx === -1) return prev;
        if (interceptorResolved === "ABORT JOB") {
          return prev.map((s, i) =>
            i === idx ? { ...s, state: "failed" as StageState } : s
          );
        }
        // occasionally complete execute → review
        if (Math.random() > 0.65 && idx < prev.length - 1) {
          return prev.map((s, i) => {
            if (i === idx) return { ...s, state: "done" as StageState };
            if (i === idx + 1) return { ...s, state: "running" as StageState };
            return s;
          });
        }
        return prev;
      });
    }, 3200);

    return () => {
      window.clearInterval(logTimer);
      window.clearInterval(metricsTimer);
      window.clearInterval(stageTimer);
    };
  }, [showInterceptor, interceptorResolved]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const copyKey = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(apiKey);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      /* ignore */
    }
  }, [apiKey]);

  const resolveInterceptor = (action: string) => {
    setInterceptorResolved(action);
    setLogs((prev) => [
      ...prev,
      {
        id: uid(),
        ts: nowStamp(),
        level: action === "ABORT JOB" ? "err" : "ok",
        source: "human",
        message: `interceptor → ${action}`,
      },
    ]);
    if (action === "FORCE MOCK MODE") setProvider("MOCK");
    if (action === "APPROVE TOOL") {
      setShowInterceptor(false);
      setStages((prev) =>
        prev.map((s) =>
          s.id === "execute" ? { ...s, state: "running" as StageState } : s
        )
      );
    }
    if (action === "ABORT JOB") {
      setJob((j) => ({ ...j, status: "failed" }));
      setShowInterceptor(false);
    }
  };

  return (
    <div className="flex h-screen min-h-0 flex-col bg-black text-[#e8e8e8] antialiased selection:bg-[#00ff66] selection:text-black">
      {/* ================================================================ */}
      {/* 1. GLOBAL STATUS HEADER                                          */}
      {/* ================================================================ */}
      <header className="sticky top-0 z-50 flex h-12 shrink-0 items-center gap-4 border-b border-[#222] bg-black px-4">
        <div className="flex min-w-0 items-center gap-3">
          <Zap className="h-4 w-4 shrink-0 text-[#00ff66]" strokeWidth={1.75} />
          <h1 className="truncate font-mono text-[13px] font-semibold tracking-[0.12em] text-white">
            T-EX LLM // RUNTIME CONSOLE
          </h1>
        </div>

        {/* Host status pill */}
        <div
          className="flex items-center gap-2 border border-[#222] bg-[#0d0d0d] px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider text-[#aaa]"
          title={healthDetail}
        >
          <span className="relative flex h-2 w-2">
            <span
              className={cn(
                "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60",
                hostStatus === "online" ? "bg-[#00ff66]" : "bg-[#666]"
              )}
            />
            <span
              className={cn(
                "relative inline-flex h-2 w-2 rounded-full",
                hostStatus === "online" ? "bg-[#00ff66]" : "bg-[#666]"
              )}
            />
          </span>
          <span className="text-[#00ff66]">HOST</span>
          <span className="text-[#555]">|</span>
          <span className="max-w-[180px] truncate text-[#888]">
            {healthDetail}
          </span>
        </div>

        {/* Provider tabs */}
        <div className="ml-auto flex items-center gap-0 border border-[#222]">
          {PROVIDERS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setProvider(p)}
              className={cn(
                "px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors",
                "border-r border-[#222] last:border-r-0",
                provider === p
                  ? "bg-[#00ff66] text-black"
                  : "bg-[#0d0d0d] text-[#888] hover:text-white"
              )}
            >
              [{p}]
            </button>
          ))}
        </div>

        {/* API key */}
        <div className="flex items-center gap-2 border border-[#222] bg-[#0d0d0d] px-2 py-1 font-mono text-[11px]">
          <Shield className="h-3.5 w-3.5 text-[#666]" strokeWidth={1.5} />
          <span className="text-[#666]">X-API-Key:</span>
          <span className="text-white">{apiKey}</span>
          <button
            type="button"
            onClick={() => void copyKey()}
            className="ml-1 border border-[#222] p-1 text-[#888] hover:border-[#00ff66] hover:text-[#00ff66]"
            aria-label="Copy API key"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-[#00ff66]" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </header>

      {/* ================================================================ */}
      {/* BODY: 1/4 | 2/4 | 1/4                                            */}
      {/* ================================================================ */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-0 lg:grid-cols-4">
        {/* ============================================================ */}
        {/* 2. LEFT — FIRMWARE REGISTRY                                  */}
        {/* ============================================================ */}
        <aside className="flex min-h-0 flex-col border-r border-[#222] lg:col-span-1">
          <Panel
            title="Firmware registry"
            icon={<HardDrive className="h-3.5 w-3.5" strokeWidth={1.5} />}
            className="min-h-0 flex-1 border-0 border-b border-[#222]"
          >
            <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.16em] text-[#555]">
              firmware/
            </p>
            <ul className="space-y-1">
              {FIRMWARE_REGISTRY.map((pkg) => {
                const active = pkg.id === activeFirmwareId;
                return (
                  <li key={pkg.id}>
                    <button
                      type="button"
                      onClick={() => setActiveFirmwareId(pkg.id)}
                      className={cn(
                        "w-full border px-2.5 py-2 text-left transition-colors",
                        active
                          ? "border-[#00ff66] bg-[#00ff66]/[0.06]"
                          : "border-[#222] bg-black hover:border-[#333]"
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <Mono
                          className={
                            active ? "text-[#00ff66]" : "text-white"
                          }
                        >
                          {pkg.id}
                        </Mono>
                        <span className="font-mono text-[10px] text-[#666]">
                          @{pkg.version}
                        </span>
                      </div>
                      <p className="mt-1 font-mono text-[10px] leading-snug text-[#666]">
                        {pkg.path}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>

            {/* Active package detail */}
            <div className="mt-4 border border-[#222] bg-black">
              <button
                type="button"
                onClick={() => setShowManifest((v) => !v)}
                className="flex w-full items-center justify-between border-b border-[#222] px-2.5 py-2 font-mono text-[11px] uppercase tracking-wider text-[#888] hover:text-white"
              >
                <span className="flex items-center gap-2">
                  <FileCode2 className="h-3.5 w-3.5" strokeWidth={1.5} />
                  {activeFirmware.id}@{activeFirmware.version}
                </span>
                <ChevronRight
                  className={cn(
                    "h-3.5 w-3.5 transition-transform",
                    showManifest && "rotate-90"
                  )}
                />
              </button>
              {showManifest && (
                <div className="space-y-3 p-2.5 font-mono text-[11px]">
                  <div>
                    <div className="mb-1 text-[10px] uppercase tracking-wider text-[#555]">
                      manifest.yaml · inputs
                    </div>
                    <ul className="space-y-0.5 text-[#aaa]">
                      {activeFirmware.inputs.map((inp) => (
                        <li key={inp.key} className="flex justify-between gap-2">
                          <span className="text-[#00ff66]">{inp.key}</span>
                          <span className="text-[#666]">
                            {inp.type}
                            {inp.required ? " · req" : ""}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div className="mb-1 text-[10px] uppercase tracking-wider text-[#555]">
                      prompt variables
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {activeFirmware.promptVars.map((v) => (
                        <span
                          key={v}
                          className="border border-[#222] bg-[#0d0d0d] px-1.5 py-0.5 text-[10px] text-[#00ff66]"
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="mb-1 text-[10px] uppercase tracking-wider text-[#555]">
                      roles
                    </div>
                    <p className="text-[#888]">
                      {activeFirmware.roles.join(" → ")}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </Panel>

          {/* Telemetry */}
          <Panel
            title="Telemetry"
            icon={<Gauge className="h-3.5 w-3.5" strokeWidth={1.5} />}
            className="h-[160px] shrink-0 border-0"
          >
            <div className="grid grid-cols-2 gap-2">
              <div className="border border-[#222] bg-black p-2.5">
                <div className="font-mono text-[10px] uppercase tracking-wider text-[#555]">
                  Token burn
                </div>
                <div className="mt-1 font-mono text-lg tabular-nums text-[#00ff66]">
                  ${tokenBurn.toFixed(4)}
                  <span className="text-[11px] text-[#666]">/min</span>
                </div>
              </div>
              <div className="border border-[#222] bg-black p-2.5">
                <div className="font-mono text-[10px] uppercase tracking-wider text-[#555]">
                  Loop speed
                </div>
                <div className="mt-1 font-mono text-lg tabular-nums text-white">
                  {loopHz.toFixed(1)}
                  <span className="text-[11px] text-[#666]"> Hz</span>
                </div>
              </div>
              <div className="col-span-2 border border-[#222] bg-black p-2.5">
                <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-[#555]">
                  <span>Provider</span>
                  <span className="text-[#00ff66]">{provider}</span>
                </div>
                <div className="mt-2 h-1 w-full bg-[#151515]">
                  <div
                    className="h-1 bg-[#00ff66] transition-all duration-500"
                    style={{ width: `${Math.min(100, loopHz * 16)}%` }}
                  />
                </div>
              </div>
            </div>
          </Panel>
        </aside>

        {/* ============================================================ */}
        {/* 3. CENTER — LIVE RUNTIME & PIPELINE                          */}
        {/* ============================================================ */}
        <main className="flex min-h-0 flex-col border-r border-[#222] lg:col-span-2">
          {/* Job runner block */}
          <Panel
            title="Live runtime"
            icon={<Activity className="h-3.5 w-3.5" strokeWidth={1.5} />}
            className="shrink-0 border-0 border-b border-[#222]"
            action={
              <span className="font-mono text-[10px] uppercase tracking-wider text-[#00ff66]">
                polling /v1/jobs/{job.id}
              </span>
            }
          >
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 font-mono text-[12px] sm:grid-cols-4">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-[#555]">
                  Job
                </div>
                <div className="text-white">{job.id}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-[#555]">
                  Status
                </div>
                <div className="flex items-center gap-1.5 text-[#facc15]">
                  <Radio className="h-3 w-3 animate-pulse" strokeWidth={2} />
                  {job.status.toUpperCase()}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-[#555]">
                  Firmware
                </div>
                <div className="text-[#00ff66]">{job.firmware}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-[#555]">
                  Iterations
                </div>
                <div className="tabular-nums text-white">{job.iterations}</div>
              </div>
              <div className="col-span-2 sm:col-span-4">
                <div className="text-[10px] uppercase tracking-wider text-[#555]">
                  Goal
                </div>
                <div className="text-[#ccc]">{job.goal}</div>
              </div>
            </div>
          </Panel>

          {/* 4-stage pipeline */}
          <Panel
            title="Pipeline stepper"
            icon={<Cpu className="h-3.5 w-3.5" strokeWidth={1.5} />}
            className="shrink-0 border-0 border-b border-[#222]"
          >
            <div className="flex flex-wrap items-center gap-0">
              {stages.map((stage, i) => (
                <div key={stage.id} className="flex items-center">
                  <div
                    className={cn(
                      "flex min-w-[108px] flex-col border px-3 py-2",
                      stage.state === "done" &&
                        "border-[#00ff66] bg-[#00ff66]/[0.08]",
                      stage.state === "running" &&
                        "border-[#facc15] bg-[#facc15]/[0.08]",
                      stage.state === "queued" && "border-[#222] bg-black",
                      stage.state === "failed" &&
                        "border-[#ff3333] bg-[#ff3333]/[0.08]"
                    )}
                  >
                    <div className="flex items-center gap-1.5 font-mono text-[11px] font-semibold tracking-[0.14em]">
                      {stage.state === "done" && (
                        <Check
                          className="h-3.5 w-3.5 text-[#00ff66]"
                          strokeWidth={2}
                        />
                      )}
                      {stage.state === "running" && (
                        <Circle
                          className="h-3 w-3 animate-pulse fill-[#facc15] text-[#facc15]"
                          strokeWidth={0}
                        />
                      )}
                      {stage.state === "queued" && (
                        <Circle
                          className="h-3 w-3 text-[#444]"
                          strokeWidth={1.5}
                        />
                      )}
                      {stage.state === "failed" && (
                        <AlertTriangle
                          className="h-3.5 w-3.5 text-[#ff3333]"
                          strokeWidth={1.75}
                        />
                      )}
                      <span
                        className={cn(
                          stage.state === "done" && "text-[#00ff66]",
                          stage.state === "running" && "text-[#facc15]",
                          stage.state === "queued" && "text-[#666]",
                          stage.state === "failed" && "text-[#ff3333]"
                        )}
                      >
                        [{stage.label}]
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-[#555]">
                      {stage.state}
                    </div>
                  </div>
                  {i < stages.length - 1 && (
                    <ChevronRight
                      className="mx-1 h-4 w-4 shrink-0 text-[#333]"
                      strokeWidth={1.5}
                    />
                  )}
                </div>
              ))}
            </div>
          </Panel>

          {/* Streaming terminal */}
          <Panel
            title="texllm.cli // stream"
            icon={<Terminal className="h-3.5 w-3.5" strokeWidth={1.5} />}
            className="min-h-[220px] flex-1 border-0"
            action={
              <span className="flex items-center gap-1 font-mono text-[10px] text-[#555]">
                <Play className="h-3 w-3 text-[#00ff66]" strokeWidth={2} />
                LIVE
              </span>
            }
          >
            <div className="h-full min-h-[200px] overflow-auto border border-[#1a1a1a] bg-black p-2 font-mono text-[11px] leading-relaxed">
              {logs.map((line) => (
                <div key={line.id} className="flex gap-2 py-0.5">
                  <span className="shrink-0 text-[#444]">{line.ts}</span>
                  <span
                    className={cn(
                      "w-10 shrink-0 uppercase",
                      line.level === "ok" && "text-[#00ff66]",
                      line.level === "info" && "text-[#6b9fff]",
                      line.level === "warn" && "text-[#facc15]",
                      line.level === "err" && "text-[#ff3333]",
                      line.level === "tool" && "text-[#c084fc]"
                    )}
                  >
                    {line.level}
                  </span>
                  <span className="w-28 shrink-0 truncate text-[#666]">
                    {line.source}
                  </span>
                  <span className="text-[#ccc]">{line.message}</span>
                </div>
              ))}
              <div ref={logEndRef} />
              <div className="mt-1 flex items-center gap-1 text-[#00ff66]">
                <span className="inline-block h-3 w-1.5 animate-pulse bg-[#00ff66]" />
                <span className="text-[#444]">_</span>
              </div>
            </div>
          </Panel>
        </main>

        {/* ============================================================ */}
        {/* 4. RIGHT — HOT-RELOAD CONTEXT + HITL                         */}
        {/* ============================================================ */}
        <aside className="flex min-h-0 flex-col lg:col-span-1">
          <Panel
            title="Playbook injector"
            icon={<FileCode2 className="h-3.5 w-3.5" strokeWidth={1.5} />}
            className="min-h-0 flex-1 border-0 border-b border-[#222]"
          >
            <div className="mb-2 flex items-center gap-2 border border-[#222] bg-black px-2 py-1.5 font-mono text-[11px]">
              <span className="text-[#555]">ACTIVE</span>
              <span className="truncate text-[#00ff66]">
                playbooks/00-orchestrator.md
              </span>
            </div>
            <pre className="overflow-auto border border-[#222] bg-black p-2.5 font-mono text-[10px] leading-relaxed text-[#888]">
{`# Playbook: Orchestrator
# Route work across T-ex layers

| Intent        | Next                |
|---------------|---------------------|
| host / deploy | playbooks/01-host   |
| team workers  | playbooks/02-workers|
| firmware      | playbooks/04-firmware|

rules:
  - team runners > solo agents
  - model-agnostic env config
  - no secrets in git`}
            </pre>
            <div className="mt-3 space-y-1">
              {[
                "playbooks/00-orchestrator.md",
                "playbooks/02-workers.md",
                "playbooks/04-firmware.md",
                "skills/t-ex/SKILL.md",
              ].map((f) => (
                <button
                  key={f}
                  type="button"
                  className="flex w-full items-center gap-2 border border-[#222] bg-[#0d0d0d] px-2 py-1.5 text-left font-mono text-[10px] text-[#888] hover:border-[#333] hover:text-white"
                >
                  <FileCode2 className="h-3 w-3 shrink-0" strokeWidth={1.5} />
                  <span className="truncate">{f}</span>
                </button>
              ))}
            </div>
          </Panel>

          {/* Human-in-the-loop interceptor */}
          <Panel
            title="HITL interceptor"
            icon={<AlertTriangle className="h-3.5 w-3.5 text-[#facc15]" strokeWidth={1.5} />}
            className="shrink-0 border-0"
          >
            {showInterceptor && !interceptorResolved ? (
              <div className="border border-[#facc15]/40 bg-[#facc15]/[0.04] p-3">
                <div className="mb-2 flex items-start gap-2">
                  <AlertTriangle
                    className="mt-0.5 h-4 w-4 shrink-0 text-[#facc15]"
                    strokeWidth={1.75}
                  />
                  <div>
                    <div className="font-mono text-[12px] font-semibold uppercase tracking-wider text-[#facc15]">
                      Execution anomaly
                    </div>
                    <p className="mt-1 font-mono text-[11px] leading-snug text-[#aaa]">
                      Executor requested{" "}
                      <span className="text-white">external_network</span>{" "}
                      outside firmware allowlist for{" "}
                      <span className="text-[#00ff66]">{job.id}</span>. Human
                      decision required.
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex flex-col gap-1.5">
                  {(
                    [
                      "APPROVE TOOL",
                      "FORCE MOCK MODE",
                      "ABORT JOB",
                    ] as const
                  ).map((action) => (
                    <button
                      key={action}
                      type="button"
                      onClick={() => resolveInterceptor(action)}
                      className={cn(
                        "flex items-center justify-center gap-2 border px-2 py-2 font-mono text-[11px] font-semibold uppercase tracking-[0.12em] transition-colors",
                        action === "APPROVE TOOL" &&
                          "border-[#00ff66] text-[#00ff66] hover:bg-[#00ff66] hover:text-black",
                        action === "FORCE MOCK MODE" &&
                          "border-[#222] text-[#ccc] hover:border-[#888] hover:text-white",
                        action === "ABORT JOB" &&
                          "border-[#ff3333] text-[#ff3333] hover:bg-[#ff3333] hover:text-black"
                      )}
                    >
                      {action === "ABORT JOB" ? (
                        <Square className="h-3 w-3" strokeWidth={2} />
                      ) : (
                        <Play className="h-3 w-3" strokeWidth={2} />
                      )}
                      [{action}]
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="border border-[#222] bg-black p-3 font-mono text-[11px] text-[#666]">
                {interceptorResolved ? (
                  <>
                    <span className="text-[#00ff66]">RESOLVED</span>
                    <span className="text-[#555]"> · </span>
                    <span className="text-white">{interceptorResolved}</span>
                    <button
                      type="button"
                      className="mt-3 block w-full border border-[#222] py-1.5 text-[10px] uppercase tracking-wider text-[#888] hover:text-white"
                      onClick={() => {
                        setInterceptorResolved(null);
                        setShowInterceptor(true);
                      }}
                    >
                      [re-arm interceptor]
                    </button>
                  </>
                ) : (
                  "No pending human interception. Pipeline autonomous."
                )}
              </div>
            )}
          </Panel>
        </aside>
      </div>
    </div>
  );
}
