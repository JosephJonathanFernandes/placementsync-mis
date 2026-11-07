import { useEffect, useState } from "react";
import { Panel } from "@/components/Panel";
import { gmailAuthService } from "@/services/api";
import type { GmailConnectionStatus } from "@/types";

export function Settings() {
  const [academicYear, setAcademicYear] = useState("2024-25");
  const [excelPath, setExcelPath] = useState("./exports/placement_register.xlsx");
  const [connection, setConnection] = useState<GmailConnectionStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    gmailAuthService
      .status()
      .then((r) => setConnection(r.data))
      .finally(() => setLoadingStatus(false));
  }, []);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const res = await gmailAuthService.authorize();
      window.location.href = res.data.authorization_url;
    } catch (err) {
      alert("Failed to start Gmail connection. Is the backend running?");
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm("Disconnect Gmail? Stored tokens will be deleted.")) return;
    try {
      await gmailAuthService.disconnect();
      setConnection({ connected: false, email_address: null, scopes: [], token_expiry: null });
    } catch (err) {
      alert("Failed to disconnect Gmail.");
    }
  };

  // Handle OAuth callback query params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const gmail = params.get("gmail");
    const reason = params.get("reason");
    if (gmail === "connected") {
      setConnection({ connected: true, email_address: null, scopes: [], token_expiry: null });
      gmailAuthService.status().then((r) => setConnection(r.data));
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (gmail === "error") {
      alert(`Gmail connection failed: ${reason ?? "unknown error"}`);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  return (
    <div className="page">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Panel>
          <h2 className="text-lg font-semibold mb-4">General</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Academic year
              </label>
              <input
                className="input"
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                placeholder="e.g. 2024-25"
              />
              <p className="text-xs text-gray-500 mt-1">
                Used for filtering placements by academic year.
              </p>
            </div>
          </div>
        </Panel>

        <Panel>
          <h2 className="text-lg font-semibold mb-4">Email connection (Gmail)</h2>
          <div className="space-y-4">
            <div className="rounded-md border p-4">
              {loadingStatus ? (
                <p className="text-sm text-gray-500">Checking connection…</p>
              ) : connection?.connected ? (
                <>
                  <p className="text-sm font-medium text-gray-900">
                    Connected: <span className="font-mono">{connection.email_address}</span>
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Scopes: {connection.scopes.join(", ")}
                  </p>
                  {connection.token_expiry && (
                    <p className="text-xs text-gray-500 mt-1">
                      Token expires: {connection.token_expiry}
                    </p>
                  )}
                  <button
                    onClick={handleDisconnect}
                    className="btn-outline px-4 py-2 text-sm font-semibold mt-3"
                  >
                    Disconnect Gmail
                  </button>
                </>
              ) : (
                <>
                  <p className="text-sm text-gray-700">
                    Gmail is not connected. PlacementSync only reads emails — it
                    never sends, deletes, or modifies them.
                  </p>
                  <button
                    onClick={handleConnect}
                    disabled={connecting}
                    className="btn-primary w-full px-4 py-2 text-sm font-semibold disabled:opacity-50"
                  >
                    {connecting ? "Connecting…" : "Connect Gmail account"}
                  </button>
                </>
              )}
            </div>
            <div className="rounded-md border border-amber-100 bg-amber-50 p-4">
              <p className="text-sm text-amber-700">
                <strong>How it works:</strong> You will be redirected to Google
                to authorize PlacementSync to read your Gmail (read-only scope
                only). After approval, you will return here and can fetch
                placement emails from the Inbox.
              </p>
              <p className="text-xs text-amber-600 mt-2">
                You must set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the
                backend .env file first.
              </p>
            </div>
          </div>
        </Panel>

        <Panel>
          <h2 className="text-lg font-semibold mb-4">Excel register</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Placement register path
              </label>
              <input
                className="input"
                value={excelPath}
                onChange={(e) => setExcelPath(e.target.value)}
              />
              <p className="text-xs text-gray-500 mt-1">
                Stored on the server; exports are downloaded from the register
                page.
              </p>
            </div>
            <div className="pt-2">
              <p className="text-xs text-gray-500">
                Changes take effect after restarting the backend.
              </p>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
