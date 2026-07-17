import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Project = {
  id: string;
  name: string;
  description: string;
  status: "active" | "paused" | "archived";
  createdAt: string;
};

type ProjectsCtx = {
  projects: Project[];
  activeProjectId: string;
  setActiveProjectId: (id: string) => void;
  addProject: (p: Omit<Project, "id" | "createdAt">) => Project;
  updateProject: (id: string, patch: Partial<Project>) => void;
};

const KEY = "texllm.projects.v1";
const ACTIVE_KEY = "texllm.activeProject.v1";
const Ctx = createContext<ProjectsCtx | null>(null);

export function ProjectsProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) return JSON.parse(raw) as Project[];
    } catch {
      /* ignore */
    }
    return [
      {
        id: "default",
        name: "Default workspace",
        description: "Primary T-ex LLM agent workspace",
        status: "active",
        createdAt: new Date().toISOString(),
      },
    ];
  });
  const [activeProjectId, setActiveProjectId] = useState(
    () => localStorage.getItem(ACTIVE_KEY) || "default"
  );

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(projects));
  }, [projects]);
  useEffect(() => {
    localStorage.setItem(ACTIVE_KEY, activeProjectId);
  }, [activeProjectId]);

  const addProject = useCallback((p: Omit<Project, "id" | "createdAt">) => {
    const project: Project = {
      ...p,
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
    };
    setProjects((prev) => [project, ...prev]);
    return project;
  }, []);

  const updateProject = useCallback((id: string, patch: Partial<Project>) => {
    setProjects((prev) =>
      prev.map((x) => (x.id === id ? { ...x, ...patch } : x))
    );
  }, []);

  const value = useMemo(
    () => ({
      projects,
      activeProjectId,
      setActiveProjectId,
      addProject,
      updateProject,
    }),
    [projects, activeProjectId, addProject, updateProject]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useProjects() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useProjects outside ProjectsProvider");
  return ctx;
}
