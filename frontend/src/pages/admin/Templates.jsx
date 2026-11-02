import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg, fmt } from "../../lib/api";
import { PageHead } from "../../components/admin/AdminLayout";
import EmailPreview from "./EmailPreview";

export default function Templates() {
  const [list, setList] = useState([]); const [sel, setSel] = useState(null); const [preview, setPreview] = useState(false);
  const load = () => api.get("/admin/templates").then((r) => { setList(r.data); setSel((s) => r.data.find((t) => t.key === s?.key) || r.data[0]); });
  useEffect(() => { load(); }, []);
  const save = async () => { try { await api.put(`/admin/templates/${sel.key}`, { subject: sel.subject, body: sel.body }); toast.success("Template saved"); load(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div>
      <PageHead title="Email Templates" desc="Placeholders: [COMPANY_NAME] [HR_NAME] [PURPOSE] [APPROVED_DATE] [START_TIME] [END_TIME] [REQUEST_ID] [DURATION] [MODE] [MEETING_LINK] [ITEM] [JNF_URL]. Verify statistics, dates and eligibility before saving." />
      <div className="grid gap-4 lg:grid-cols-4">
        <div className="card h-fit p-2">{list.map((t) => <button key={t.key} onClick={() => setSel(t)} className={`block w-full rounded px-3 py-2 text-left text-sm ${sel?.key === t.key ? "bg-[#2563EB] text-white" : "hover:bg-[#DBEAFE]"}`} data-testid={`tpl-${t.key}`}>{t.name}</button>)}</div>
        {sel && (
          <div className="card space-y-3 p-5 lg:col-span-3">
            <label className="block"><span className="lbl">Subject</span><input className="field" value={sel.subject} onChange={(e) => setSel({ ...sel, subject: e.target.value })} data-testid="tpl-subject" /></label>
            <label className="block"><span className="lbl">Body (plain text)</span><textarea className="field font-mono text-xs" rows={24} value={sel.body} onChange={(e) => setSel({ ...sel, body: e.target.value })} data-testid="tpl-body" /></label>
            <div className="flex items-center gap-3"><button className="btn-primary" onClick={save} data-testid="tpl-save-btn">Save template</button><button className="btn-outline" onClick={() => setPreview(true)} data-testid="tpl-preview-btn">Preview</button><span className="text-xs text-[#64748B]">Last updated {fmt(sel.updated_at)}</span></div>
          </div>
        )}
      </div>
      {preview && sel && <EmailPreview tplKey={sel.key} draft={{ subject: sel.subject, body: sel.body }} onClose={() => setPreview(false)} />}
    </div>
  );
}
