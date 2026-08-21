import { createSupabaseServerClient } from "@/lib/supabase/server";
import type { LeadStatus } from "@/lib/supabase/types";

const STATUS_LABELS: Record<LeadStatus, string> = {
  new: "New",
  contacted: "Contacted",
  replied: "Replied",
  qualified: "Qualified",
  booked: "Booked",
  human_review: "Needs human review",
  lost: "Lost",
  opted_out: "Opted out",
};

const STATUS_BADGE_CLASSES: Record<LeadStatus, string> = {
  new: "bg-slate-100 text-slate-700",
  contacted: "bg-blue-100 text-blue-700",
  replied: "bg-indigo-100 text-indigo-700",
  qualified: "bg-teal-100 text-teal-700",
  booked: "bg-green-100 text-green-700",
  human_review: "bg-amber-100 text-amber-800",
  lost: "bg-red-100 text-red-700",
  opted_out: "bg-slate-200 text-slate-600",
};

export default async function LeadsPage() {
  const supabase = await createSupabaseServerClient();

  // RLS scopes this to the caller's own tenant (or all tenants for
  // platform_admin) — no manual tenant_id filter is needed or trusted here.
  const { data: leads, error } = await supabase
    .from("leads")
    .select("id, name, phone, email, source, status, sms_consent, created_at, first_response_due_at")
    .order("created_at", { ascending: false })
    .limit(100);

  if (error) {
    return <p className="text-sm text-red-600">Could not load leads: {error.message}</p>;
  }

  return (
    <div>
      <h1 className="mb-6 text-lg font-semibold">Leads</h1>
      {leads.length === 0 ? (
        <p className="text-sm text-slate-500">No leads yet.</p>
      ) : (
        <div className="overflow-hidden rounded border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Contact</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">SMS consent</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Received</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leads.map((lead) => (
                <tr key={lead.id}>
                  <td className="px-4 py-3">{lead.name ?? "—"}</td>
                  <td className="px-4 py-3">{lead.phone ?? lead.email ?? "—"}</td>
                  <td className="px-4 py-3 capitalize">{lead.source.replace("_", " ")}</td>
                  <td className="px-4 py-3">{lead.sms_consent ? "Yes" : "No"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded px-2 py-1 text-xs font-medium ${STATUS_BADGE_CLASSES[lead.status]}`}
                    >
                      {STATUS_LABELS[lead.status]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {new Date(lead.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
