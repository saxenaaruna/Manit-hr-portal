import { useEffect, useState } from "react";
import { api, fmt } from "../../lib/api";
import { PageHead } from "../../components/admin/AdminLayout";

export default function Activity() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/admin/activity").then((r) => setRows(r.data)); }, []);
  return (
    <div>
      <PageHead title="Activity History" desc="Latest 500 actions across companies, requests, emails, templates and settings." />
      <div className="overflow-x-auto rounded-lg border border-[#D6E4F7] bg-white">
        <table className="w-full min-w-[900px] text-sm" data-testid="activity-table">
          <thead className="bg-[#DBEAFE] text-left text-xs uppercase text-[#123B70]"><tr>{["Time", "Actor", "Entity", "Action", "Previous", "New"].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.id} className="border-t border-[#EEF3FB] text-xs">
              <td className="px-3 py-2 whitespace-nowrap">{fmt(r.timestamp)}</td><td className="px-3 py-2">{r.admin_id}</td><td className="px-3 py-2">{r.entity_type} · <span className="font-mono">{String(r.entity_id).slice(0, 12)}</span></td>
              <td className="px-3 py-2 font-medium">{r.action}</td><td className="max-w-[220px] truncate px-3 py-2">{r.previous_value || "—"}</td><td className="max-w-[260px] truncate px-3 py-2">{r.new_value || "—"}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
