import { useState } from "react";
import { Panel } from "@/components/Panel";
import { backupService } from "@/services/api";

export function Backup() {
  const [dbBackupLoading, setDbBackupLoading] = useState(false);
  const [excelBackupLoading, setExcelBackupLoading] = useState(false);
  const [restoreLoading, setRestoreLoading] = useState(false);
  const [restoreInfo, setRestoreInfo] = useState<{
    message: string;
    steps: string[];
    note: string;
  } | null>(null);

  const handleDbBackup = async () => {
    setDbBackupLoading(true);
    try {
      const res = await backupService.database();
      const blob = res.data as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const cd = res.headers["content-disposition"] || "";
      const match = cd.match(/filename="?([^";]+)"?/);
      a.download = match ? match[1] : "placement_sync_backup.db";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to download database backup.");
    } finally {
      setDbBackupLoading(false);
    }
  };

  const handleExcelBackup = async () => {
    setExcelBackupLoading(true);
    try {
      const res = await backupService.excel();
      const blob = res.data as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const cd = res.headers["content-disposition"] || "";
      const match = cd.match(/filename="?([^";]+)"?/);
      a.download = match ? match[1] : "placement_register_backup.xlsx";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      if (err.response?.status === 404) {
        alert("No Excel placement register found yet.");
      } else {
        alert("Failed to download Excel backup.");
      }
    } finally {
      setExcelBackupLoading(false);
    }
  };

  const handleRestoreInfo = async () => {
    setRestoreLoading(true);
    try {
      const res = await backupService.restore();
      setRestoreInfo(res.data);
    } catch (err) {
      alert("Failed to load restore instructions.");
    } finally {
      setRestoreLoading(false);
    }
  };

  return (
    <div className="page">
      <h1 className="text-2xl font-bold mb-6">Backup & Recovery</h1>

      <Panel>
        <h2 className="text-lg font-semibold mb-4">Database Backup</h2>
        <p className="text-gray-500 text-sm mb-4">
          Download a copy of the SQLite placement database. The live database is
          not modified during backup.
        </p>
        <button
          onClick={handleDbBackup}
          disabled={dbBackupLoading}
          className="btn-primary px-4 py-2 text-sm font-semibold disabled:opacity-50"
        >
          {dbBackupLoading ? "Backing up…" : "Download Database Backup"}
        </button>
      </Panel>

      <div className="mt-6">
        <Panel>
          <h2 className="text-lg font-semibold mb-4">Excel Register Backup</h2>
          <p className="text-gray-500 text-sm mb-4">
            Download a copy of the placement register Excel file.
          </p>
          <button
            onClick={handleExcelBackup}
            disabled={excelBackupLoading}
            className="btn-primary px-4 py-2 text-sm font-semibold disabled:opacity-50"
          >
            {excelBackupLoading ? "Backing up…" : "Download Excel Backup"}
          </button>
        </Panel>
      </div>

      <div className="mt-6">
        <Panel>
          <h2 className="text-lg font-semibold mb-4">Restore Procedure</h2>
          <p className="text-gray-500 text-sm mb-4">
            Database restore is an operational procedure to prevent accidental
            data loss.
          </p>
          <button
            onClick={handleRestoreInfo}
            disabled={restoreLoading}
            className="btn-outline px-4 py-2 text-sm font-semibold disabled:opacity-50 mb-4"
          >
            {restoreLoading ? "Loading…" : "Show Restore Instructions"}
          </button>
          {restoreInfo && (
            <div className="rounded-md border border-gray-200 bg-gray-50 p-4 mt-4">
              <h3 className="text-sm font-semibold mb-2">Restore Steps</h3>
              <ol className="text-sm text-gray-700 list-decimal pl-6 space-y-1">
                {restoreInfo.steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
              <p className="text-xs text-gray-500 mt-3">
                {restoreInfo.note}
              </p>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
