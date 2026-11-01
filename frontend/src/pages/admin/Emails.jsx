import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg, fmt } from "../../lib/api";
import { PageHead } from "../../components/admin/AdminLayout";
import Modal, { Field } from "../../components/Modal";

const TYPES = ["Recruitment Invitation", "JNF Reminder", "Campus Visit Confirmation", "Call Confirmation", "Rescheduling Update", "Cancellation Update", "Manual Communication"];

export default function Emails() {
  const [rows, setRows] = useState([]); const [type, setType] = useState(""); const [compose, setCompose] = useState(false);
  const load = useCallback(() => api.get("/admin/emails", { params: { type } }).then((r) => setRows(r.data)), [type]);
  useEffect(() => { load(); }, [load]);
  const retry = async (id) => { try { const r = (await api.post(`/admin/emails/${id}/retry`)).data; (r.ok ? toast.success : toast.error)(r.message); load(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div>
      <PageHead title="Email Communication" desc="All official emails are sent through the Gmail API as tpwnitb@gmail.com. 'Sent' means Gmail accepted the message (not a delivery receipt).">
        <select className="field w-auto" value={type} onChange={(e) => setType(e.target.value)} data-testid="email-type-filter"><option value="">All types</option>{TYPES.map((t) => <option key={t}>{t}</option>)}</select>
        <button className="btn-primary" onClick={() => setCompose(true)} data-testid="compose-email-btn">Send manual email</button>
      </PageHead>
      <div className="overflow-x-auto rounded-lg border border-[#D6E4F7] bg-white">
        <table className="w-full min-w-[1100px] text-sm" data-testid="emails-table">
          <thead className="bg-[#DBEAFE] text-left text-xs uppercase text-[#123B70]"><tr>{["Recipient", "Company", "HR", "Type", "Subject", "Date & Time", "Status", "Provider Message ID", "Request ID", ""].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.id} className="border-t border-[#EEF3FB] align-top" data-testid={`email-row-${i}`}>
                <td className="px-3 py-2 text-xs">{r.recipient_email}</td><td className="px-3 py-2">{r.company_name || "—"}</td><td className="px-3 py-2 text-xs">{r.hr_name || "—"}</td>
                <td className="px-3 py-2 text-xs">{r.email_type}</td><td className="max-w-[260px] px-3 py-2 text-xs">{r.subject}</td><td className="px-3 py-2 text-xs">{fmt(r.sent_at || r.created_at)}</td>
                <td className="px-3 py-2 text-xs"><span className={`font-semibold ${r.delivery_status === "Sent" ? "text-green-700" : "text-red-600"}`} data-testid={`email-status-${i}`}>{r.delivery_status}</span>{r.error && <p className="max-w-[220px] text-[11px] text-[#64748B]">{r.error}</p>}</td>
                <td className="px-3 py-2 font-mono text-[11px]">{r.provider_message_id || "—"}</td><td className="px-3 py-2 font-mono text-[11px]">{r.related_request_id || "—"}</td>
                <td className="px-3 py-2">{r.delivery_status === "Failed" && <button className="btn-outline px-2 py-1 text-xs" onClick={() => retry(r.id)} data-testid={`email-retry-${i}`}>Retry</button>}</td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={10} className="p-8 text-center text-[#64748B]">No emails yet.</td></tr>}
          </tbody>
        </table>
      </div>
      {compose && <Compose onClose={() => setCompose(false)} onDone={load} />}
    </div>
  );
}

function Compose({ onClose, onDone }) {
  const [f, setF] = useState({ to: "", subject: "", body: "" }); const [busy, setBusy] = useState(false);
  const send = async () => {
    if (!window.confirm(`Send this email to ${f.to} from tpwnitb@gmail.com?`)) return;
    setBusy(true);
    try { const r = (await api.post("/admin/emails/manual", f)).data; (r.ok ? toast.success : toast.error)(r.message); onDone(); onClose(); } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <Modal open onClose={onClose} title="Send manual communication" testid="compose-modal">
      <Field label="To"><input className="field" value={f.to} onChange={(e) => setF({ ...f, to: e.target.value })} data-testid="compose-to" /></Field>
      <Field label="Subject"><input className="field" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} data-testid="compose-subject" /></Field>
      <Field label="Body"><textarea className="field" rows={8} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} data-testid="compose-body" /></Field>
      <button className="btn-primary" disabled={busy} onClick={send} data-testid="compose-send-btn">Send</button>
    </Modal>
  );
}
