import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search, MoreHorizontal } from "lucide-react";
import { api, errMsg, STATUS_STYLE, fmt } from "../../lib/api";
import { PageHead } from "../../components/admin/AdminLayout";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "../../components/ui/dropdown-menu";
import LeadDetail from "./LeadDetail";
import ScheduleCallDialog from "./ScheduleCallDialog";
import EmailPreview from "./EmailPreview";

export const showInvite = (inv) => {
  if (!inv) return;
  if (inv.ok) toast.success(inv.message);
  else if (inv.skipped) toast.info(inv.message);
  else toast.error(inv.message, { duration: 8000 });
};

const INV_STYLE = { Sent: "text-green-700", Failed: "text-red-600", Queued: "text-blue-600", "Not Sent": "text-slate-500" };
const BLANK = { company_name: "", hr_name: "", contact_number: "", work_email: "", interest_status: "Warm", remarks: "", recruitment_request: "" };

const Cell = ({ value, onSave, testid, type = "text" }) => {
  const [v, setV] = useState(value || "");
  useEffect(() => { setV(value || ""); }, [value]);
  return <input className="cell" type={type} value={v} onChange={(e) => setV(e.target.value)} onBlur={() => v !== (value || "") && onSave(v)} onKeyDown={(e) => e.key === "Enter" && e.target.blur()} data-testid={testid} />;
};

const AiHint = ({ r, onApply, onRefresh }) => {
  const s = r.ai_status_suggestion;
  if (!s?.status) return <button className="text-[#1D4ED8] hover:underline" onClick={onRefresh} title="Suggest from remarks & request">Suggest</button>;
  return (
    <span className="flex items-center gap-1">
      <span className={`rounded border px-1.5 ${STATUS_STYLE[s.status]}`}>{s.status} {Math.round(s.confidence * 100)}%</span>
      {s.status !== r.interest_status && <button className="text-[#1D4ED8] hover:underline" onClick={() => window.confirm(`Change status to ${s.status}?${s.status === "Hot" ? " This sends the invitation email." : ""}`) && onApply(s.status)} data-testid="ai-apply-btn">Apply</button>}
    </span>
  );
};

export default function Leads() {
  const [rows, setRows] = useState([]);
  const [stats, setStats] = useState({});
  const [q, setQ] = useState(""); const [status, setStatus] = useState(""); const [sort, setSort] = useState("updated_at|desc");
  const [nw, setNw] = useState(BLANK);
  const [detail, setDetail] = useState(null); const [callFor, setCallFor] = useState(null); const [preview, setPreview] = useState(null);

  const load = useCallback(async () => {
    const [field, order] = sort.split("|");
    const [r, s] = await Promise.all([api.get("/admin/leads", { params: { q, status, sort: field, order } }), api.get("/admin/stats")]);
    setRows(r.data); setStats(s.data);
  }, [q, status, sort]);
  useEffect(() => { load(); }, [load]);

  const save = async (id, patch) => {
    try { const r = await api.patch(`/admin/leads/${id}`, patch); showInvite(r.data.invitation); if (!r.data.invitation) toast.success("Saved"); load(); if ("remarks" in patch || "recruitment_request" in patch) setTimeout(load, 3000); }
    catch (e) { toast.error(errMsg(e)); load(); }
  };
  const add = async () => {
    try { const r = await api.post("/admin/leads", nw); showInvite(r.data.invitation); toast.success("Company added"); setNw(BLANK); load(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const invite = async (id) =>{ try { showInvite((await api.post(`/admin/leads/${id}/invite`)).data); load(); } catch (e) { toast.error(errMsg(e)); } };
  const suggest = async (id) => { try { const s = (await api.post(`/admin/leads/${id}/suggest-status`)).data; s.status ? toast.info(`AI suggests ${s.status} (${Math.round(s.confidence * 100)}%)`) : toast.error(s.error); load(); } catch (e) { toast.error(errMsg(e)); } };
  const del = async (r) => { if (!window.confirm(`Delete ${r.company_name}? This cannot be undone.`)) return; await api.delete(`/admin/leads/${r.id}`); toast.success("Deleted"); load(); };

  const chips = [["", "All", stats.total], ["Hot", "Hot", stats.hot], ["Warm", "Warm", stats.warm], ["Cold", "Cold", stats.cold]];
  return (
    <div>
      <PageHead title="Company Leads Spreadsheet" desc="Edit any cell and press Enter or click away to save. Changing status to Hot sends the invitation & JNF email automatically (once)." />
      <div className="mb-4 flex flex-wrap gap-3 text-xs">
        {[["Invitations Sent", stats.invitations_sent], ["JNFs Awaited", stats.jnf_awaited], ["JNFs Received", stats.jnf_received]].map(([l, v]) => (
          <span key={l} className="rounded-md border border-[#D6E4F7] bg-white px-3 py-1.5 text-[#123B70]">{l}: <b>{v ?? "–"}</b></span>
        ))}
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex rounded-md border border-[#C9D8F0] bg-white p-0.5">
          {chips.map(([v, l, c]) => (
            <button key={l} onClick={() => setStatus(v)} className={`rounded px-3 py-1.5 text-sm ${status === v ? "bg-[#2563EB] text-white" : "text-[#123B70] hover:bg-[#DBEAFE]"}`} data-testid={`filter-${l.toLowerCase()}`}>{l} <span className="opacity-70">{c ?? ""}</span></button>
          ))}
        </div>
        <div className="relative"><Search className="absolute left-2.5 top-2.5 h-4 w-4 text-[#64748B]" /><input className="field w-64 pl-8" placeholder="Search company or HR name" value={q} onChange={(e) => setQ(e.target.value)} data-testid="leads-search" /></div>
        <select className="field w-auto" value={sort} onChange={(e) => setSort(e.target.value)} data-testid="leads-sort">
          <option value="updated_at|desc">Recently updated</option><option value="company_name|asc">Company name A–Z</option>
          <option value="interest_status|asc">Status</option><option value="last_contact_at|desc">Last contacted</option>
        </select>
      </div>
      <div className="overflow-x-auto rounded-lg border border-[#D6E4F7] bg-white">
        <table className="sheet w-full min-w-[1400px] border-collapse text-sm" data-testid="leads-table">
          <thead className="bg-[#DBEAFE] text-left text-xs uppercase tracking-wide text-[#123B70]">
            <tr>{["#", "Company Name", "HR Name", "HR Contact Number", "HR Mail ID", "Status", "AI Suggestion", "Remarks", "Request", "Invitation Status", "JNF Status", "Last Contacted", ""].map((h) => <th key={h} className="px-2 py-2 font-semibold">{h}</th>)}</tr>
          </thead>
          <tbody>
            <tr className="bg-[#EFF6FF]" data-testid="new-lead-row">
              <td className="px-2 text-[#64748B]"><Plus className="h-4 w-4" /></td>
              {["company_name", "hr_name", "contact_number", "work_email"].map((k) => <td key={k}><input className="cell" placeholder={k === "company_name" ? "New company…" : ""} value={nw[k]} onChange={(e) => setNw({ ...nw, [k]: e.target.value })} data-testid={`new-${k}`} /></td>)}
              <td><select className="cell" value={nw.interest_status} onChange={(e) => setNw({ ...nw, interest_status: e.target.value })} data-testid="new-interest_status">{["Hot", "Warm", "Cold"].map((s) => <option key={s}>{s}</option>)}</select></td>
              <td></td>
              <td><input className="cell" value={nw.remarks} onChange={(e) => setNw({ ...nw, remarks: e.target.value })} data-testid="new-remarks" /></td>
              <td><input className="cell" value={nw.recruitment_request} onChange={(e) => setNw({ ...nw, recruitment_request: e.target.value })} data-testid="new-recruitment_request" /></td>
              <td colSpan={4} className="px-2"><button className="btn-primary py-1" onClick={add} disabled={!nw.company_name.trim()} data-testid="add-lead-btn">Add row</button></td>
            </tr>
            {rows.map((r, i) => (
              <tr key={r.id} className="hover:bg-[#F7FAFF]" data-testid={`lead-row-${i}`}>
                <td className="px-2 text-xs text-[#64748B]">{i + 1}</td>
                <td className="min-w-[170px] font-medium"><Cell value={r.company_name} onSave={(v) => save(r.id, { company_name: v })} testid={`cell-company-${i}`} /></td>
                <td className="min-w-[140px]"><Cell value={r.hr_name} onSave={(v) => save(r.id, { hr_name: v })} testid={`cell-hr-${i}`} /></td>
                <td className="min-w-[130px]"><Cell value={r.contact_number} onSave={(v) => save(r.id, { contact_number: v })} testid={`cell-phone-${i}`} /></td>
                <td className="min-w-[200px]"><Cell value={r.work_email} onSave={(v) => save(r.id, { work_email: v })} testid={`cell-email-${i}`} /></td>
                <td className="w-24 px-1"><select className={`cell rounded border font-semibold ${STATUS_STYLE[r.interest_status]}`} value={r.interest_status} onChange={(e) => save(r.id, { interest_status: e.target.value })} data-testid={`cell-status-${i}`}>{["Hot", "Warm", "Cold"].map((s) => <option key={s}>{s}</option>)}</select></td>
                <td className="min-w-[120px] px-2 text-xs" data-testid={`cell-ai-${i}`}><AiHint r={r} onApply={(s) => save(r.id, { interest_status: s })} onRefresh={() => suggest(r.id)} /></td>
                <td className="min-w-[200px]"><Cell value={r.remarks} onSave={(v) => save(r.id, { remarks: v })} testid={`cell-remarks-${i}`} /></td>
                <td className="min-w-[200px]"><Cell value={r.recruitment_request} onSave={(v) => save(r.id, { recruitment_request: v })} testid={`cell-request-${i}`} /></td>
                <td className={`px-2 text-xs font-semibold ${INV_STYLE[r.invitation_status]}`} title={r.invitation_error || ""} data-testid={`cell-invitation-${i}`}>{r.invitation_status}{r.invitation_status === "Failed" && <span className="block font-normal text-red-500">Email setup required</span>}</td>
                <td className="w-28"><select className="cell" value={r.jnf_status} onChange={(e) => save(r.id, { jnf_status: e.target.value })} data-testid={`cell-jnf-${i}`}><option>Awaited</option><option>Received</option></select></td>
                <td className="px-2 text-xs text-[#64748B]">{fmt(r.last_contact_at)}</td>
                <td className="px-1">
                  <DropdownMenu>
                    <DropdownMenuTrigger className="rounded p-1 hover:bg-[#DBEAFE]" data-testid={`row-actions-${i}`}><MoreHorizontal className="h-4 w-4" /></DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => setDetail(r.id)} data-testid={`action-details-${i}`}>View details & history</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setPreview(r)} data-testid={`action-preview-${i}`}>Preview invitation</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => invite(r.id)} data-testid={`action-invite-${i}`}>{r.invitation_success_at ? "Resend invitation" : "Send invitation"}</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setCallFor(r)} data-testid={`action-call-${i}`}>Schedule call</DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem className="text-red-600" onClick={() => del(r)} data-testid={`action-delete-${i}`}>Delete</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={13} className="p-8 text-center text-[#64748B]">No companies found.</td></tr>}
          </tbody>
        </table>
      </div>
      {detail && <LeadDetail id={detail} onClose={() => setDetail(null)} onChanged={load} />}
      {callFor && <ScheduleCallDialog lead={callFor} onClose={() => setCallFor(null)} />}
      {preview && <EmailPreview lead={preview} onClose={() => setPreview(null)} onSend={() => { const id = preview.id; setPreview(null); invite(id); }} />}
    </div>
  );
}
