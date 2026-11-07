import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Panel } from "@/components/Panel";
import {
  emailService,
  extractionService,
  gmailAuthService,
  gmailService,
} from "@/services/api";
import type { EmailOut } from "@/types";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

const cn = (...classes: string[]) => twMerge(clsx(classes));

export function Inbox() {
  const [emails, setEmails] = useState<EmailOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [labels, setLabels] = useState<{ id: string; name: string }[]>([]);
  const [selectedLabel, setSelectedLabel] = useState("");
  const [query, setQuery] = useState(
    'selected OR congratulations OR placement OR "offer letter" OR joining OR shortlisted'
  );
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    emailService
      .list()
      .then((r) => setEmails(r.data))
      .finally(() => setLoading(false));
    gmailAuthService
      .status()
      .then((r) => setGmailConnected(r.data.connected))
      .catch(() => setGmailConnected(false));
    if (gmailConnected) {
      gmailService.listLabels().then((r) => setLabels(r.data.labels));
    }
  }, [gmailConnected]);

  const buildGmailQuery = () => {
    const parts: string[] = [];
    if (query.trim()) parts.push(query.trim());
    if (selectedLabel) parts.push(`label:${selectedLabel}`);
    if (dateFrom) parts.push(`after:${dateFrom}`);
    if (dateTo) parts.push(`before:${dateTo}`);
    return parts.join(" ");
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setLoading(true);
      const uploaded = await emailService.upload(file);
      const emailId = uploaded.data.email_id;
      await extractionService.run(emailId);
      setEmails((prev) =>
        prev.map((em) =>
          em.id === emailId ? { ...em, is_processed: true } : em
        ),
      );
      navigate(`/review/${emailId}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchGmail = async () => {
    setFetching(true);
    try {
      const gmailQuery = buildGmailQuery();
      const res = await gmailService.process({
        query: gmailQuery,
        max_results: 50,
      });
      const s = res.data.summary;
      alert(
        `Gmail fetch complete:\n${s.fetched} fetched\n${s.stored} new\n${s.skipped_duplicate} duplicates\n${s.created_review_results} ready for review\n${s.attachment_errors} attachment errors\n${s.errors} errors`
      );
      setEmails(await (await emailService.list()).data);
    } catch (err: any) {
      alert(`Failed to fetch from Gmail: ${err.response?.data?.detail || err.message}`);
    } finally {
      setFetching(false);
    }
  };

  return (
    <div className="page">
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">Email Inbox</h1>
          <p className="text-gray-500 text-sm">
            Retrieve placement emails and run extraction. Uploaded emails are
            never modified — PlacementSync only reads.
          </p>
        </div>
        <div className="flex items-end gap-2">
          <label className="btn-outline block">
            Upload .eml
            <input
              type="file"
              accept=".eml"
              className="hidden"
              onChange={handleUpload}
            />
          </label>
        </div>
      </div>

      {gmailConnected ? (
        <div className="mb-6">
          <Panel>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
            <div className="flex flex-col">
              <label className="text-xs font-medium text-gray-500 mb-1">
                Keywords
              </label>
              <input
                className="input input-sm"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="selected OR congratulations"
              />
            </div>
            <div className="flex flex-col">
              <label className="text-xs font-medium text-gray-500 mb-1">
                Label
              </label>
              <select
                className="input input-sm"
                value={selectedLabel}
                onChange={(e) => setSelectedLabel(e.target.value)}
              >
                <option value="">All labels</option>
                {labels.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col">
              <label className="text-xs font-medium text-gray-500 mb-1">
                From date
              </label>
              <input
                className="input input-sm"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>
            <div className="flex flex-col">
              <label className="text-xs font-medium text-gray-500 mb-1">
                To date
              </label>
              <input
                className="input input-sm"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleFetchGmail}
              disabled={fetching}
              className="btn-primary px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {fetching ? "Fetching…" : "Fetch from Gmail"}
            </button>
            <p className="text-xs text-gray-500">
              Read-only — emails are only read, never modified.
            </p>
          </div>
        </Panel>
        </div>
      ) : (
        <div className="mb-6">
          <button
            onClick={() => {
              gmailAuthService.authorize().then((res) => {
                window.location.href = res.data.authorization_url;
              });
            }}
            className="btn-primary px-4 py-2 text-sm font-semibold"
          >
            Connect Gmail account
          </button>
          <p className="text-sm text-gray-500 mt-1">
            Connect Gmail to fetch placement emails automatically. Otherwise,
            upload .eml files manually.
          </p>
        </div>
      )}

      <Panel>
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Sender</th>
                <th>Source</th>
                <th>Status</th>
                <th>Received</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="h-24 text-center text-gray-500">
                    Loading emails…
                  </td>
                </tr>
              ) : emails.length === 0 ? (
                <tr>
                  <td colSpan={6} className="h-24 text-center text-gray-500">
                    No emails yet. Upload a .eml file or fetch from Gmail.
                  </td>
                </tr>
              ) : (
                emails.map((email) => (
                  <tr key={email.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="font-medium truncate max-w-xs">
                      {email.subject ?? "(no subject)"}
                    </td>
                    <td className="text-sm text-gray-600 truncate max-w-xs">
                      {email.sender ?? "—"}
                    </td>
                    <td className="text-sm">{email.source}</td>
                    <td>
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
                          email.is_processed
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-600",
                        )}
                      >
                        {email.is_processed ? "Processed" : "New"}
                      </span>
                    </td>
                    <td className="text-sm text-gray-600">
                      {email.received_at ?? "—"}
                    </td>
                    <td className="text-right">
                      <Link
                        to={`/review/${email.id}`}
                        className="btn-outline text-xs px-3 py-1.5"
                      >
                        Review
                      </Link>
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
