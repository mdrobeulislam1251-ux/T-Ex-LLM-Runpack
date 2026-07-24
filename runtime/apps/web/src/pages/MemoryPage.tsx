import { FormEvent, useEffect, useState } from "react";

type MemoryItem = {
  id: string;
  key: string;
  value: string;
  scope: "user" | "project" | "global";
};

const KEY = "texllm.memory.v1";

export function MemoryPage() {
  const [items, setItems] = useState<MemoryItem[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(KEY) || "[]") as MemoryItem[];
    } catch {
      return [];
    }
  });
  const [k, setK] = useState("");
  const [v, setV] = useState("");
  const [scope, setScope] = useState<MemoryItem["scope"]>("project");

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(items));
  }, [items]);

  function onAdd(e: FormEvent) {
    e.preventDefault();
    if (!k.trim()) return;
    setItems((prev) => [
      {
        id: crypto.randomUUID(),
        key: k.trim(),
        value: v.trim(),
        scope,
      },
      ...prev,
    ]);
    setK("");
    setV("");
  }

  return (
    <div>
      <h1>Memory</h1>
      <p className="lede">
        Durable notes agents can lean on (local for now; host memory store later).
      </p>
      <form className="card" onSubmit={onAdd}>
        <div className="field">
          <label htmlFor="mk">Key</label>
          <input id="mk" value={k} onChange={(e) => setK(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="mv">Value</label>
          <textarea id="mv" value={v} onChange={(e) => setV(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="ms">Scope</label>
          <select
            id="ms"
            value={scope}
            onChange={(e) => setScope(e.target.value as MemoryItem["scope"])}
          >
            <option value="user">user</option>
            <option value="project">project</option>
            <option value="global">global</option>
          </select>
        </div>
        <button type="submit" className="btn btn-primary">
          Save memory
        </button>
      </form>
      <div className="card" style={{ marginTop: "1rem", overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Scope</th>
              <th>Key</th>
              <th>Value</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id}>
                <td>
                  <span className="chip">{it.scope}</span>
                </td>
                <td className="mono">{it.key}</td>
                <td>{it.value}</td>
                <td>
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost"
                    onClick={() =>
                      setItems((prev) => prev.filter((x) => x.id !== it.id))
                    }
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!items.length && <p className="empty-hint">No memories yet.</p>}
      </div>
    </div>
  );
}
