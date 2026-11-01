import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg, fmt } from "../../lib/api";
import { PageHead } from "../../components/admin/AdminLayout";
import LeadDetail from "./LeadDetail";

export default function Jnf() {
  const [rows, setRows] = useState([]); const [filter, setFilter] = useState("Awaited"); const [url, setUrl] = useState(""); const [detail, setDetail] = useState(null);
  const load = useCallback(() => api.get("/admin/leads").then((r) => setRows(r.data)), []);
  useEffect(() => { load(); api.get("/admin/settings").then((r) => setUrl(r.data.jnf_url || "")); }, [load]);
  const patch = async (id, p) => { try { await api.patch(`/admin/leads/${id}`, p); toast.success("Saved"); load(); } catch (e) { toast.error(errMsg(e)); } };
  const saveUrl = async () => { try { await api.put("/admin/settings", { jnf_url: url }); toast.success("JNF URL updated — new emails will use it"); } catch (e) { toast.error(errMsg(e)); } };
  const remind = async (id) => { const r = (await api.post(`/admin/leads/${id}/jnf-reminder`)).data; (r.ok ? toast.success : toast.error)(r.message); load(); };
  const list = rows.filter((r) => !filter || r.jnf_status === filter);
  return (
    <div>
      <PageHead title="JNF Tracking" desc="Sending an invitation does not mean the JNF has been received. Mark JNFs as received once the company submits." />
      <div className="card mb-6 flex flex-wrap items-end gap-3 p-4">
        <label className="flex-1"><span className="lbl">Official JNF URL</span><input className="field" value={url} onChange={(e) => setUrl(e.target.value)} data-testid="jnf-url-input" /></label>
        <button className="btn-primary" onClick={saveUrl} data-testid="jnf-url-save">Update URL</button>
        <a href={url} target="_blank" rel="noreferrer" className="btn-outline">Open JNF</a>
      </div>
      <div className="mb-3 flex gap-1">{["Awaited", "Received", ""].map((s) => <button key={s} onClick={() => setFilter(s)} className={`rounded px-3 py-1.5 text-xs ${filter === s ? "bg-[#2563EB] text-white" : "border border-[#C9D8F0] bg-white"}`} data-testid={`jnf-filter-${s || "all"}`}>{s || "All"}</button>)}</div>
      <div className="overflow-x-auto rounded-lg border border-[#D6E4F7] bg-white">
        <table className="w-full min-w-[900px] text-sm" data-testid="jnf-table">
          <thead className="bg-[#DBEAFE] text-left text-xs uppercase text-[#123B70]"><tr>{["Company", "HR", "Invitation", "JNF Status", "JNF Remarks", ""].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
          <tbody>
            {list.map((r, i) => (
              <tr key={r.id} className="border-t border-[#EEF3FB]" data-testid={`jnf-row-${i}`}>
                <td className="px-3 py-2 font-medium">{r.company_name}</td><td className="px-3 py-2 text-xs">{r.hr_name}<br />{r.work_email}</td>
                <td className="px-3 py-2 text-xs">{r.invitation_status} · {fmt(r.invitation_sent_at)}</td>
                <td className="px-3 py-2"><select className="field py-1" value={r.jnf_status} onChange={(e) => patch(r.id, { jnf_status: e.target.value })} data-testid={`jnf-status-${i}`}><option>Awaited</option><option>Received</option></select></td>
                <td className="px-3 py-2"><input className="field py-1" defaultValue={r.jnf_remarks || ""} onBlur={(e) => e.target.value !== (r.jnf_remarks || "") && patch(r.id, { jnf_remarks: e.target.value })} data-testid={`jnf-remarks-${i}`} /></td>
                <td className="px-3 py-2 whitespace-nowrap"><button className="btn-outline px-2 py-1 text-xs" onClick={() => setDetail(r.id)}>Company & history</button> <button className="btn-outline px-2 py-1 text-xs" onClick={() => remind(r.id)} data-testid={`jnf-remind-${i}`}>Send reminder</button></td>
              </tr>
            ))}
            {!list.length && <tr><td colSpan={6} className="p-8 text-center text-[#64748B]">No companies.</td></tr>}
          </tbody>
        </table>
      </div>
      {detail && <LeadDetail id={detail} onClose={() => setDetail(null)} onChanged={load} />}
    </div>
  );
}
