import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type TaskStatus = "todo" | "in_progress" | "done" | "blocked";

export type Task = {
  id: string;
  userId: string;
  projectId: string;
  title: string;
  details: string;
  status: TaskStatus;
  createdAt: string;
  updatedAt: string;
};

type NewTask = {
  userId: string;
  projectId: string;
  title: string;
  details?: string;
  status?: TaskStatus;
};

type TaskCtx = {
  tasks: Task[];
  open: boolean;
  setOpen: (v: boolean) => void;
  addTask: (t: NewTask) => Task;
  updateTask: (id: string, patch: Partial<Task>) => void;
  removeTask: (id: string) => void;
  clearDone: () => void;
};

const KEY = "texllm.tasks.v1";
const Ctx = createContext<TaskCtx | null>(null);

function uid() {
  return crypto.randomUUID();
}

const SEED: Task[] = [
  {
    id: "seed-1",
    userId: "operator",
    projectId: "default",
    title: "Complete onboarding wizard",
    details: "Configure DB, domain, company vision, and theme",
    status: "todo",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "seed-2",
    userId: "operator",
    projectId: "default",
    title: "Run first team job",
    details: "Dispatch a goal from Jobs board",
    status: "todo",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

export function TaskProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [tasks, setTasks] = useState<Task[]>(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Task[];
        if (Array.isArray(parsed) && parsed.length) return parsed;
      }
    } catch {
      /* ignore */
    }
    return SEED;
  });

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(tasks));
  }, [tasks]);

  const addTask = useCallback((t: NewTask) => {
    const now = new Date().toISOString();
    const task: Task = {
      id: uid(),
      userId: t.userId,
      projectId: t.projectId,
      title: t.title,
      details: t.details || "",
      status: t.status || "todo",
      createdAt: now,
      updatedAt: now,
    };
    setTasks((prev) => [task, ...prev]);
    return task;
  }, []);

  const updateTask = useCallback((id: string, patch: Partial<Task>) => {
    setTasks((prev) =>
      prev.map((t) =>
        t.id === id
          ? { ...t, ...patch, updatedAt: new Date().toISOString() }
          : t
      )
    );
  }, []);

  const removeTask = useCallback((id: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearDone = useCallback(() => {
    setTasks((prev) => prev.filter((t) => t.status !== "done"));
  }, []);

  const value = useMemo(
    () => ({
      tasks,
      open,
      setOpen,
      addTask,
      updateTask,
      removeTask,
      clearDone,
    }),
    [tasks, open, addTask, updateTask, removeTask, clearDone]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTaskStore() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTaskStore outside TaskProvider");
  return ctx;
}
