import { useEffect, useState } from "react";
import { Panel } from "@/components/Panel";
import {
  gmailAuthService,
  schedulerService,
} from "@/services/api";
import type {
  GmailConnectionStatus,
  PollStatus,
} from "@/types";

export function Settings() {
  const [academicYear, setAcademicYear] = useState("2024-25");
  const [excelPath, setExcelPath] = useState("./exports/placement_register.xlsx");
  const [connection, setConnection] = useState<GmailConnectionStatus | null>(null);
  const [pollStatus, setPollStatus] = useState<PollStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [pollLoading, setPollLoading] = useState(false);

  useEffect(() => {
    gmailAuthService
      .status()
      .then((r) => setConnection(r.data))
      .finally(() => setLoadingStatus(false));

    schedulerService
      .pollStatus()
      .then((r) => setPollStatus(r.data))
      .catch(() => setPollStatus(null));
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

  const handleTogglePolling = async () => {
    if (!pollStatus) return;
    setPollLoading(true);
    try {
      const res = await schedulerService.updatePollStatus({
        polling_enabled: !pollStatus.polling_enabled,
        poll_interval_minutes: pollStatus.poll_interval_minutes,
      });
      setPollStatus(res.data);
      alert(
        res.data.polling_enabled
          ? "Automatic email polling enabled."
          : "Automatic email polling disabled.",
      );
    } catch (err: any) {
      alert("Failed to update polling settings: " + err.message);
    } finally {
      setPollLoading(false);
    }
  };

  const handleIntervalChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10);
    if (val < 1 || val > 1440) return;
    setPollLoading(true);
    schedulerService
      .updatePollStatus({
        polling_enabled: pollStatus?.polling_enabled ?? false,
        poll_interval_minutes: val,
      })
      .then((r) => setPollStatus(r.data))
      .catch(() => {})
      .finally(() => setPollLoading(false));
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
          <h2 className="text-lg font-semibold mb-4">Automatic email polling</h2>
          <div className="space-y-4">
            <div className="rounded-md border p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-700">
                  Automatic email fetching
                </span>
                <button
                  onClick={handleTogglePolling}
                  disabled={pollLoading}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    pollStatus?.polling_enabled
                      ? "bg-indigo-100 text-indigo-700"
                      : "bg-gray-200 text-gray-600"
                  }`}
                >
                  {pollStatus?.polling_enabled ? "Enabled" : "Disabled"}
                </button>
              </div>
              {pollStatus?.polling_enabled ? (
                <>
                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-medium text-gray-500">
                      Poll every
                    </label>
                    <input
                      type="number"
                      className="input w-24"
                      min="1"
                      max="1440"
                      value={pollStatus.poll_interval_minutes}
                      onChange={handleIntervalChange}
                      disabled={pollLoading}
                    />
                    <span className="text-xs text-gray-500">minutes</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    The backend will automatically fetch new placement emails
                    from Gmail at this interval.
                  </p>
                </>
              ) : (
                <p className="text-xs text-gray-500 mt-1">
                  Enable automatic polling to have PlacementSync periodically
                  check your Gmail for new placement emails.
                </p>
              )}
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
