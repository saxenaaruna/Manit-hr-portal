import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import Modal, { Field } from "../../components/Modal";
import { api, errMsg, fmt, STATUS_STYLE } from "../../lib/api";
import { showInvite } from "./Leads";
import EmailPreview from "./EmailPreview";

export default function LeadDetail({ id, onClose, onChanged }) {
  const [d, setD] = useState(null);
  const [f, setF] = useState({});
  const [preview, setPreview] = useState(false);
  const load = () => api.get(`/admin/leads/${id}`).then((r) => { setD(r.data); setF(r.data.lead); });
  useEffect(() => { load(); }, [id]); // eslint-disable-line
  const save = async () => {
    const keys = ["company_name", "hr_name", "designation", "work_email", "contact_number", "interest_status", "remarks", "recruitment_request", "jnf_status", "jnf_remarks"];
    try { const r = await api.patch(`/admin/leads/${id}`, Object.fromEntries(keys.map((k) => [k, f[k] ?? ""]))); showInvite(r.data.invitation); toast.success("Saved"); load(); onChanged(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const invite = async () => { showInvite((await api.post(`/admin/leads/${id}/invite`)).data); load(); onChanged(); };
  const reminder = async () => { const r = (await api.post(`/admin/leads/${id}/jnf-reminder`)).data; r.ok ? toast.success(r.message) : toast.error(r.message); load(); };
  if (!d) return null;
  const l = d.lead;
  const inp = (k, label) => <Field label={label}><input className="field" value={f[k] || ""} onChange={(e) => setF({ ...f, [k]: e.target.value })} data-testid={`detail-${k}`} /></Field>;
  return (
    <Modal open onClose={onClose} title={l.company_name} wide testid="lead-detail-modal">
      <div className="grid gap-3 sm:grid-cols-3">
        {inp("company_name", "Company")}{inp("hr_name", "HR Name")}{inp("designation", "Designation")}
        {inp("work_email", "HR Email")}{inp("contact_number", "Contact")}
        <Field label="Status"><select className="field" value={f.interest_status} onChange={(e) => setF({ ...f, interest_status: e.target.value })} data-testid="detail-status">{["Hot", "Warm", "Cold"].map((s) => <option key={s}>{s}</option>)}</select></Field>
        <div className="sm:col-span-3">{inp("recruitment_request", "Recruitment Request")}</div>
        <div className="sm:col-span-3"><Field label="Remarks (private, admin only)"><textarea className="field" rows={2} value={f.remarks || ""} onChange={(e) => setF({ ...f, remarks: e.target.value })} data-testid="detail-remarks" /></Field></div>
        <Field label="JNF Status"><select className="field" value={f.jnf_status} onChange={(e) => setF({ ...f, jnf_status: e.target.value })}><option>Awaited</option><option>Received</option></select></Field>
        <div className="sm:col-span-2">{inp("jnf_remarks", "JNF Remarks")}</div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" onClick={save} data-testid="detail-save-btn">Save changes</button>
        <button className="btn-outline" onClick={() => setPreview(true)} data-testid="detail-preview-btn">Preview invitation</button>
        <button className="btn-outline" onClick={invite} data-testid="detail-invite-btn">{l.invitation_success_at ? "Resend invitation" : "Send invitation"}</button>
        <button className="btn-outline" onClick={reminder} data-testid="detail-jnf-reminder-btn">Send JNF reminder</button>
      </div>
      <div className="grid gap-4 text-sm md:grid-cols-2">
        <div className="rounded-md bg-[#EFF6FF] p-3">
          <p className="lbl">Invitation</p>
          <p>Status: <b data-testid="detail-invitation-status">{l.invitation_status}</b> · Last sent: {fmt(l.invitation_sent_at)}</p>
          {l.invitation_message_id && <p className="text-xs">Gmail message ID: {l.invitation_message_id}</p>}
          {l.invitation_error && <p className="text-xs text-red-600">{l.invitation_error}</p>}
          <p className="mt-1">Last contacted: {fmt(l.last_contact_at)}</p>
        </div>
        <div className="rounded-md bg-[#EFF6FF] p-3">
          <p className="lbl">Status history</p>
          {(l.status_history || []).slice().reverse().map((h, i) => <p key={i} className="text-xs"><span className={`mr-2 rounded border px-1.5 ${STATUS_STYLE[h.status]}`}>{h.status}</span>{fmt(h.at)}</p>)}
        </div>
      </div>
      <History title="Email history" rows={d.emails} cols={[["email_type", "Type"], ["delivery_status", "Status"], ["provider_message_id", "Message ID"], ["created_at", "Date", fmt]]} testid="detail-emails" />
      <History title="Campus visit requests" link="/admin/visits" rows={d.visits} cols={[["id", "ID"], ["visit_purpose", "Purpose"], ["requested_date", "Requested"], ["approved_date", "Approved"], ["status", "Status"]]} />
      <History title="Call requests" link="/admin/calls" rows={d.calls} cols={[["id", "ID"], ["preferred_date", "Preferred"], ["approved_date", "Approved"], ["approved_time", "Time"], ["status", "Status"]]} />
      {preview && <EmailPreview lead={l} onClose={() => setPreview(false)} onSend={() => { setPreview(false); invite(); }} />}
    </Modal>
  );
}

const History = ({ title, rows, cols, link, testid }) => (
  <div data-testid={testid}>
    <p className="lbl">{title} {link && <Link to={link} className="ml-2 normal-case text-[#1D4ED8]">open →</Link>}</p>
    {rows.length ? (
      <table className="w-full text-xs"><tbody>{rows.map((r) => <tr key={r.id} className="border-b border-[#EEF3FB]">{cols.map(([k, , f]) => <td key={k} className="py-1 pr-2">{f ? f(r[k]) : r[k] || "—"}</td>)}</tr>)}</tbody></table>
    ) : <p className="text-xs text-[#64748B]">None</p>}
  </div>
);
