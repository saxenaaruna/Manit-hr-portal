import { useEffect, useRef, useState } from "react";
import { MessageCircle, X, Send } from "lucide-react";
import { API } from "../../lib/api";

const GREETING = "Hello! Welcome to MANIT Bhopal's Training & Placement Portal. I'm MANIT Connect, your AI assistant for recruitment information and campus visit coordination. Are you interested in campus recruitment, internships, or connecting with our Training & Placement Cell?";

export default function ChatWidget({ open, setOpen }) {
  const [msgs, setMsgs] = useState([{ role: "assistant", text: GREETING }]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const sid = useRef(`s_${Math.random().toString(36).slice(2)}${Date.now()}`);
  const end = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, typing]);

  const update = (fn) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = fn(c[c.length - 1]); return c; });
  const send = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || typing) return;
    setInput(""); setTyping(true);
    setMsgs((m) => [...m, { role: "user", text }, { role: "assistant", text: "" }]);
    try {
      const res = await fetch(`${API}/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sid.current, message: text }) });
      if (!res.ok) throw new Error();
      const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n"); buf = parts.pop();
        for (const p of parts) {
          if (!p.startsWith("data: ")) continue;
          const d = JSON.parse(p.slice(6));
          if (d.delta) update((l) => ({ ...l, text: l.text + d.delta }));
          if (d.error) update((l) => ({ ...l, text: d.error, error: true }));
          if (d.note) setMsgs((m) => [...m, { role: "assistant", text: d.note, system: true }]);
        }
      }
    } catch { update((l) => ({ ...l, text: "Sorry, I couldn't connect right now. Please try again or email tpwnitb@gmail.com.", error: true })); }
    setTyping(false);
  };

  return (
    <>
      {!open && (
        <button onClick={() => setOpen(true)} className="fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-full bg-[#1D4ED8] px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-900/30 transition-transform hover:-translate-y-0.5" data-testid="chat-open-btn">
          <MessageCircle className="h-5 w-5" />Chat with MANIT Connect
        </button>
      )}
      {open && (
        <div className="fixed bottom-0 right-0 z-50 flex h-[85vh] w-full flex-col overflow-hidden border border-[#BFD3F5] bg-white shadow-2xl sm:bottom-5 sm:right-5 sm:h-[600px] sm:w-[400px] sm:rounded-xl fade-up" data-testid="chat-window">
          <div className="flex items-center justify-between bg-[#0B2545] px-4 py-3 text-white">
            <div><p className="font-semibold">MANIT Connect</p><p className="text-xs text-blue-200">AI assistant · Training & Placement Cell</p></div>
            <button onClick={() => setOpen(false)} aria-label="Close chat" data-testid="chat-close-btn"><X className="h-5 w-5" /></button>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto bg-[#EFF6FF] p-4" data-testid="chat-messages">
            {msgs.map((m, i) => {
              const text = m.role === "assistant" ? m.text.split("<action")[0].trim() : m.text;
              if (m.role === "assistant" && !text && typing && i === msgs.length - 1) return null;
              return (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div data-testid={`chat-msg-${m.role}`} className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${m.role === "user" ? "bg-[#1D4ED8] text-white" : m.system ? "border border-[#93B4EC] bg-[#DBEAFE] text-[#0B2545]" : m.error ? "border border-red-200 bg-red-50 text-red-700" : "border border-[#D6E4F7] bg-white text-[#172B4D]"}`}>{text}</div>
                </div>
              );
            })}
            {typing && !msgs[msgs.length - 1].text && <div className="dot-typing text-2xl leading-none text-[#2563EB]" data-testid="chat-typing"><span>.</span><span>.</span><span>.</span></div>}
            <div ref={end} />
          </div>
          <form onSubmit={send} className="flex gap-2 border-t border-[#D6E4F7] p-3">
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type your message…" className="field" data-testid="chat-input" />
            <button className="btn-primary px-3" disabled={typing} aria-label="Send" data-testid="chat-send-btn"><Send className="h-4 w-4" /></button>
          </form>
        </div>
      )}
    </>
  );
}
