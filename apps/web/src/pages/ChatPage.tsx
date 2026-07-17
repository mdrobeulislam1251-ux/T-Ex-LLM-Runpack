import { FormEvent, useEffect, useRef, useState } from "react";
import { FriendlyAgentOnboard } from "../components/FriendlyAgentOnboard";
import { friendlyChat, getAliases, type AgentAliases } from "../lib/api";
import { useSettings } from "../state/settings";

type Msg = { role: "user" | "agent"; content: string };

export function ChatPage() {
  const { settings } = useSettings();
  const [aliases, setAliases] = useState<AgentAliases | null>(null);
  const agentName = aliases?.agent_name || "Tex";
  const userName = aliases?.user_name || "Operator";

  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "agent",
      content: "Hi! Loading your agent names…",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const a = await getAliases(settings);
        if (!alive) return;
        setAliases(a);
        setMessages([
          {
            role: "agent",
            content: `Hi ${a.user_name}! I'm ${a.agent_name}. Ask about jobs, onboarding, firmware, or team runners.`,
          },
        ]);
      } catch {
        if (!alive) return;
        setAliases(null);
        setMessages([
          {
            role: "agent",
            content:
              "Hi Operator! I'm Tex. Ask about jobs, onboarding, firmware, or team runners.",
          },
        ]);
      }
    })();
    return () => {
      alive = false;
    };
  }, [settings]);

  async function onSend(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    try {
      const res = await friendlyChat(settings, text, aliases);
      setMessages((m) => [...m, res]);
    } finally {
      setBusy(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <div>
      <h1>Friendly chat</h1>
      <p className="lede">
        You → agent: <strong>{agentName}</strong>
        {" · "}
        Agent → you: <strong>{userName}</strong>
        {" · "}
        Change names in Settings.
      </p>
      <FriendlyAgentOnboard
        name={agentName}
        title={`Always kind, always clear — ${agentName}`}
        message={`I address you as ${userName}. Configure aliases under Settings → Agent aliases.`}
      />
      <div className="card">
        <div className="chat-log" aria-live="polite">
          {messages.map((m, i) => (
            <div key={i} className={"chat-bubble " + m.role}>
              <strong style={{ fontSize: "0.75rem", color: "var(--tex-muted)" }}>
                {m.role === "user" ? userName : agentName}
              </strong>
              <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
        <form onSubmit={onSend} style={{ marginTop: "0.85rem" }}>
          <div className="field">
            <label htmlFor="chat-in">Message to {agentName}</label>
            <textarea
              id="chat-in"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Hey ${agentName}, how do I connect Supabase?`}
              rows={3}
            />
          </div>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Thinking…" : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}
