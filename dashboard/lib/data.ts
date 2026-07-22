import fs from "fs";
import path from "path";

// The dashboard lives inside the T-Ex LLM repo; the repo root is one level up.
export const REPO_ROOT = path.resolve(process.cwd(), "..");
const COMPANIES_DIR = path.join(REPO_ROOT, "companies");
const AGENTS_DIR = path.join(REPO_ROOT, "plugins", "tex-llm", "agents");
const SKILLS_DIR = path.join(REPO_ROOT, "plugins", "tex-llm", "skills");
const COMMANDS_DIR = path.join(REPO_ROOT, "plugins", "tex-llm", "commands");

export interface AgentInfo {
  name: string;
  team: string;
  description: string;
}

export interface TeamInfo {
  id: string;
  label: string;
  agents: AgentInfo[];
}

export interface CompanyInfo {
  slug: string;
  name: string;
  appName: string;
  description: string;
  vision: string;
  emotionTone: string;
  scopeDoes: string;
  scopeDoesNot: string;
  targetAudience: string;
  status: "complete" | "draft" | "invalid";
  hasCredentials: boolean;
}

export interface DashboardData {
  activeSlug: string | null;
  companies: CompanyInfo[];
  teams: TeamInfo[];
  agentCount: number;
  skillCount: number;
  commandCount: number;
  decisions: string;
  incidents: string;
}

export const TEAM_LABELS: Record<string, string> = {
  executive: "Executive",
  engineering: "Engineering",
  design: "Design",
  ai: "AI",
  "issue-fixers": "Issue Fixers",
  technical: "Technical",
  marketing: "Marketing",
  sales: "Sales",
  research: "Research & Strategy",
};

function readFrontmatter(file: string): { name: string; description: string } | null {
  try {
    const content = fs.readFileSync(file, "utf-8");
    const match = content.match(/^---\nname: (?<name>[a-z0-9-]+)\ndescription: (?<desc>.+)\n---/);
    if (!match?.groups) return null;
    return { name: match.groups.name, description: match.groups.desc };
  } catch {
    return null;
  }
}

export function loadRoster(): TeamInfo[] {
  if (!fs.existsSync(AGENTS_DIR)) return [];
  return Object.keys(TEAM_LABELS)
    .filter((team) => fs.existsSync(path.join(AGENTS_DIR, team)))
    .map((team) => {
      const dir = path.join(AGENTS_DIR, team);
      const agents = fs
        .readdirSync(dir)
        .filter((f) => f.endsWith(".md"))
        .map((f) => {
          const fm = readFrontmatter(path.join(dir, f));
          return fm ? { name: fm.name, team, description: fm.description } : null;
        })
        .filter((a): a is AgentInfo => a !== null);
      return { id: team, label: TEAM_LABELS[team], agents };
    });
}

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function loadCompanies(): { activeSlug: string | null; companies: CompanyInfo[] } {
  let activeSlug: string | null = null;
  const companies: CompanyInfo[] = [];
  if (!fs.existsSync(COMPANIES_DIR)) return { activeSlug, companies };

  const activeFile = path.join(COMPANIES_DIR, "active-company.json");
  if (fs.existsSync(activeFile)) {
    try {
      activeSlug = JSON.parse(fs.readFileSync(activeFile, "utf-8")).active ?? null;
    } catch {
      activeSlug = null;
    }
  }

  for (const entry of fs.readdirSync(COMPANIES_DIR, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const profilePath = path.join(COMPANIES_DIR, entry.name, "profile.json");
    if (!fs.existsSync(profilePath)) continue;
    try {
      const p = JSON.parse(fs.readFileSync(profilePath, "utf-8"));
      const requestPending = fs.existsSync(path.join(COMPANIES_DIR, entry.name, "brain-request.json"));
      const dbEnv = p?.credentials?.database?.env ?? {};
      const hasCredentials = Boolean(str(dbEnv.host) && str(dbEnv.password));
      companies.push({
        slug: entry.name,
        name: str(p?.company?.name) || entry.name,
        appName: str(p?.company?.app_name),
        description: str(p?.company?.description),
        vision: str(p?.brain?.vision),
        emotionTone: str(p?.brain?.emotion_tone),
        scopeDoes: str(p?.brain?.scope?.does),
        scopeDoesNot: str(p?.brain?.scope?.does_not),
        targetAudience: str(p?.brain?.target_audience),
        status: requestPending ? "draft" : "complete",
        hasCredentials,
      });
    } catch {
      companies.push({
        slug: entry.name,
        name: entry.name,
        appName: "",
        description: "profile.json could not be parsed",
        vision: "",
        emotionTone: "",
        scopeDoes: "",
        scopeDoesNot: "",
        targetAudience: "",
        status: "invalid",
        hasCredentials: false,
      });
    }
  }
  return { activeSlug, companies };
}

function readLog(slug: string | null, file: string): string {
  if (!slug) return "";
  const p = path.join(COMPANIES_DIR, slug, file);
  try {
    return fs.existsSync(p) ? fs.readFileSync(p, "utf-8") : "";
  } catch {
    return "";
  }
}

function countDir(dir: string, predicate: (name: string) => boolean): number {
  try {
    return fs.existsSync(dir) ? fs.readdirSync(dir).filter(predicate).length : 0;
  } catch {
    return 0;
  }
}

export function loadDashboardData(): DashboardData {
  const teams = loadRoster();
  const { activeSlug, companies } = loadCompanies();
  return {
    activeSlug,
    companies,
    teams,
    agentCount: teams.reduce((n, t) => n + t.agents.length, 0),
    skillCount: countDir(SKILLS_DIR, () => true),
    commandCount: countDir(COMMANDS_DIR, (f) => f.endsWith(".md")),
    decisions: readLog(activeSlug, "decisions.md"),
    incidents: readLog(activeSlug, "incidents.md"),
  };
}

export function slugify(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
