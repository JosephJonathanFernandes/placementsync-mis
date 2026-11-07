import { useEffect, useState } from "react";
import { Panel } from "@/components/Panel";
import { recordsService, excelService } from "@/services/api";
import type { PlacementRecordWithDetails } from "@/types";

export function Register() {
  const [records, setRecords] = useState<PlacementRecordWithDetails[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ company: "", branch: "", status: "" });
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    recordsService.list(filters).then((r) => setRecords(r.data)).finally(() => setLoading(false));
  }, [filters.company, filters.branch, filters.status]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await excelService.export();
        const blob = res.data as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "placement_register.xlsx";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="page">
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">Placement Register</h1>
          <p className="text-gray-500 text-sm">
            Approved placement records. Use the Excel export to publish the
            official register.
          </p>
        </div>
        <div className="flex items-end gap-2">
          <button
            onClick={handleExport}
            disabled={exporting}
            className="btn-primary px-4 py-2 text-sm font-semibold disabled:opacity-50"
          >
            {exporting ? "Exporting…" : "Export to Excel"}
          </button>
        </div>
      </div>

      <Panel>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="flex flex-col">
            <label className="text-xs font-medium text-gray-500 mb-1">Company</label>
            <input
              className="input"
              value={filters.company}
              onChange={(e) => setFilters({ ...filters, company: e.target.value })}
            />
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-medium text-gray-500 mb-1">Branch</label>
            <input
              className="input"
              value={filters.branch}
              onChange={(e) => setFilters({ ...filters, branch: e.target.value })}
            />
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-medium text-gray-500 mb-1">Status</label>
            <input
              className="input"
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Reg. No.</th>
                <th>Branch</th>
                <th>Company</th>
                <th>Role</th>
                <th>CTC</th>
                <th>Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="h-32 text-center text-gray-500">
                    Loading…
                  </td>
                </tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan={8} className="h-32 text-center text-gray-500">
                    No records yet. Approve students from the review queue.
                  </td>
                </tr>
              ) : (
                records.map((r) => (
                  <tr key={r.id} className="border-b border-gray-100">
                    <td>{r.student_name}</td>
                    <td className="text-sm">{r.student_registration_number ?? "—"}</td>
                    <td className="text-sm">{r.student_branch ?? "—"}</td>
                    <td className="font-medium">{r.company_name}</td>
                    <td className="text-sm">{r.job_role ?? "—"}</td>
                    <td className="text-sm">{r.package ?? "—"}</td>
                    <td className="text-sm">{r.selection_date ?? "—"}</td>
                    <td className="text-sm">{r.status}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
