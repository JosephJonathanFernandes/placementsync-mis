import { useEffect, useState } from "react";
import { Panel } from "@/components/Panel";
import { auditService } from "@/services/api";
import type { AuditLogOut } from "@/types";

export function Audit() {
  const [logs, setLogs] = useState<AuditLogOut[]>([]);
  const [summary, setSummary] = useState<Record<string, Record<string, number>>>(
    {}
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      auditService.list().then((r) => setLogs(r.data)),
      auditService.summary().then((r) => setSummary(r.data)),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page">
      <h1 className="text-2xl font-bold mb-6">Audit Log</h1>

      <div className="mb-6">
        <Panel>
          <h2 className="text-lg font-semibold mb-4">Summary</h2>
          {Object.entries(summary).length === 0 ? (
            <p className="text-gray-500">No audit activity yet.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(summary).map(([table, actions]) => (
                <div key={table} className="rounded-md border border-gray-200 bg-gray-50 p-4">
                  <h3 className="text-sm font-semibold text-gray-900 mb-2">
                    {table}
                  </h3>
                  <ul className="text-sm text-gray-600 space-y-1">
                    {Object.entries(actions).map(([action, count]) => (
                      <li key={action}>
                        {action}: <span className="font-medium">{count}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel>
        <h2 className="text-lg font-semibold mb-4">Log Entries</h2>
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Table</th>
                <th>Record ID</th>
                <th>Action</th>
                <th>Changed By</th>
                <th>Changed At</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="h-24 text-center text-gray-500">
                    No audit log entries yet.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="border-b border-gray-100">
                    <td className="font-mono text-sm">{log.id}</td>
                    <td className="text-sm">{log.table_name}</td>
                    <td className="text-sm font-mono">
                      {log.record_id ?? "—"}
                    </td>
                    <td className="text-sm font-medium capitalize">
                      {log.action}
                    </td>
                    <td className="text-sm">{log.changed_by ?? "—"}</td>
                    <td className="text-sm font-mono text-gray-500">
                      {log.changed_at ?? "—"}
                    </td>
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
