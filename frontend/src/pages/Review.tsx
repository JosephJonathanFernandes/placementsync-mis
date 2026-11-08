import { useEffect, useState } from "react";

import { Panel } from "@/components/Panel";
import {
  extractionService,
  bulkExtractionService,
} from "@/services/api";
import type {
  ApprovalAction,
  ExtractedStudent,
  ExtractionResultWithEmail,
} from "@/types";

function emptyStudent(): ExtractedStudent {
  return { name: "", registration_number: "", branch: "", job_role: "", package: "" };
}

export function Review() {
  const [items, setItems] = useState<ExtractionResultWithEmail[]>([]);
  const [selected, setSelected] = useState<ExtractionResultWithEmail | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [bulkSaving, setBulkSaving] = useState(false);

  const load = () => {
    setLoading(true);
    extractionService
      .listPending()
      .then((r) => setItems(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const openDetail = (item: ExtractionResultWithEmail) => setSelected(item);
  const closeDetail = () => setSelected(null);

  const handleApprove = async (item: ExtractionResultWithEmail) => {
    setSaving(true);
    try {
      const action: ApprovalAction = {
        action: "approve",
        edited_company: item.company_name ?? undefined,
        edited_students: item.extracted_students.map((s) => ({
          name: s.name,
          registration_number: s.registration_number,
          branch: s.branch,
          job_role: s.job_role,
          package: s.package,
        })),
      };
      await extractionService.approve(Number(item.id), action);
      setSelected(null);
      load();
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async (item: ExtractionResultWithEmail) => {
    setSaving(true);
    try {
      await extractionService.reject(Number(item.id), { action: "reject" });
      setSelected(null);
      load();
    } finally {
      setSaving(false);
    }
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((i) => i.id)));
    }
  };

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return;
    setBulkSaving(true);
    try {
      const resultIds = Array.from(selectedIds);
      const res = await bulkExtractionService.approve(resultIds);
      alert(res.data.message);
      if (res.data.errors.length > 0) {
        alert("Errors:\n" + res.data.errors.join("\n"));
      }
      setSelectedIds(new Set());
      load();
    } catch (err: any) {
      alert("Bulk approve failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setBulkSaving(false);
    }
  };

  const handleBulkReject = async () => {
    if (selectedIds.size === 0) return;
    setBulkSaving(true);
    try {
      const resultIds = Array.from(selectedIds);
      const res = await bulkExtractionService.reject(resultIds);
      alert(res.data.message);
      setSelectedIds(new Set());
      load();
    } catch (err: any) {
      alert("Bulk reject failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setBulkSaving(false);
    }
  };

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page">
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">Review Queue</h1>
          <p className="text-gray-500 text-sm">
            Extraction results await your verification. Nothing is written to
            the placement register until you approve.
          </p>
        </div>
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-700">
              {selectedIds.size} selected
            </span>
            <button
              onClick={handleBulkApprove}
              disabled={bulkSaving}
              className="btn-primary px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {bulkSaving ? "Approving…" : "Approve Selected"}
            </button>
            <button
              onClick={handleBulkReject}
              disabled={bulkSaving}
              className="btn-outline px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {bulkSaving ? "Rejecting…" : "Reject Selected"}
            </button>
          </div>
        )}
      </div>

      {selected ? (
        <div className="lg:max-w-4xl">
          <div className="flex items-center gap-2 mb-4">
            <button
              onClick={closeDetail}
              className="btn-outline text-sm px-3 py-1.5"
            >
              ← Back to queue
            </button>
            <span className="text-sm font-medium text-gray-700">
              Review extraction · item #{selected.id}
            </span>
          </div>
          <ReviewDetail
            item={selected}
            onApprove={handleApprove}
            onReject={handleReject}
            saving={saving}
          />
        </div>
      ) : (
        <Panel>
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th className="w-10">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === items.length && items.length > 0}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th>Email subject</th>
                  <th>Sender</th>
                  <th>Company</th>
                  <th>Students</th>
                  <th>Confidence</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="h-24 text-center text-gray-500">
                      Nothing pending review. All caught up!
                    </td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr
                      key={item.id}
                      className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer group"
                      onClick={() => {
                        if (selectedIds.has(item.id)) {
                          toggleSelect(item.id);
                        } else {
                          openDetail(item);
                        }
                      }}
                    >
                      <td className="text-center">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(item.id)}
                          onChange={(e) => {
                            e.stopPropagation();
                            toggleSelect(item.id);
                          }}
                        />
                      </td>
                      <td className="font-medium truncate max-w-xs">
                        {item.email_subject ?? "(no subject)"}
                      </td>
                      <td className="text-sm text-gray-600 truncate max-w-xs">
                        {item.email_sender ?? "—"}
                      </td>
                      <td className="text-sm">{item.company_name ?? "—"}</td>
                      <td className="text-sm">
                        {item.extracted_students.map((s: ExtractedStudent) => s.name).join(", ") ||
                          "—"}
                      </td>
                      <td>
                        <span className="text-sm font-mono text-gray-700">
                          {(item.confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openDetail(item);
                          }}
                          className="btn-outline text-xs px-3 py-1.5"
                        >
                          Open
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-sm text-gray-500">
            {items.length} item(s) awaiting review. Shortlisting announcements
            cannot be approved — shortlisted students are not selected students.
          </p>
        </Panel>
      )}
    </div>
  );
}

function ReviewDetail({
  item,
  onApprove,
  onReject,
  saving,
}: {
  item: ExtractionResultWithEmail;
  onApprove: (item: ExtractionResultWithEmail) => void;
  onReject: (item: ExtractionResultWithEmail) => void;
  saving: boolean;
}) {
  const [company, setCompany] = useState(item.company_name ?? "");
  const [students, setStudents] = useState(
    item.extracted_students.map((s: ExtractedStudent) => ({ ...s })),
  );
  const [editing, setEditing] = useState(false);

  const missing = item.missing_fields;
  const warnings = item.warnings;

  const updateStudent = (index: number, field: keyof ExtractedStudent, value: string) => {
    setStudents((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const addStudent = () => {
    setStudents([...students, emptyStudent()]);
  };

  const removeStudent = (index: number) => {
    setStudents(students.filter((_: ExtractedStudent, i: number) => i !== index));
  };

  const raw = item.raw_extraction;

  return (
    <Panel>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-5">
          <div>
            <h2 className="text-lg font-semibold mb-1">Original email</h2>
            <div className="rounded-md border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700 max-h-96 overflow-y-auto font-mono">
              <div>From: {item.email_sender ?? "—"}</div>
              <div>Subject: {item.email_subject ?? "—"}</div>
              <div className="mt-2 whitespace-pre-wrap">{item.email_body ?? ""}</div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Extracted company</h3>
            <div className="flex items-center gap-2">
              <input
                className="input"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                disabled={!editing}
              />
              {!editing ? (
                <button
                  onClick={() => setEditing(true)}
                  className="btn-outline text-xs px-2 py-1.5"
                >
                  Edit
                </button>
              ) : (
                <button
                  onClick={() => setEditing(false)}
                  className="text-xs text-indigo-600 hover:underline"
                >
                  Cancel
                </button>
              )}
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Extracted students</h3>
            <div className="rounded-md border border-gray-200 bg-white p-3">
              <table className="table">
                <thead>
                  <tr>
                    <th style={{ width: "22%" }}>Name</th>
                    <th style={{ width: "16%" }}>Reg. No.</th>
                    <th style={{ width: "12%" }}>Branch</th>
                    <th style={{ width: "22%" }}>Role</th>
                    <th style={{ width: "14%" }}>Package</th>
                    <th className="text-right">Conf.</th>
                    <th style={{ width: "10%" }} className="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((s: ExtractedStudent, i: number) => (
                    <tr key={i} className="border-b border-gray-100 last:border-0">
                      <td>
                        <input
                          className="input input-sm"
                          value={s.name ?? ""}
                          onChange={(e) =>
                            updateStudent(i, "name", e.target.value)}
                          disabled={!editing}
                        />
                      </td>
                      <td>
                        <input
                          className="input input-sm"
                          value={s.registration_number ?? ""}
                          onChange={(e) =>
                            updateStudent(i, "registration_number", e.target.value)
                          }
                          disabled={!editing}
                        />
                      </td>
                      <td>
                        <input
                          className="input input-sm"
                          value={s.branch ?? ""}
                          onChange={(e) => updateStudent(i, "branch", e.target.value)}
                          disabled={!editing}
                        />
                      </td>
                      <td>
                        <input
                          className="input input-sm"
                          value={s.job_role ?? ""}
                          onChange={(e) => updateStudent(i, "job_role", e.target.value)}
                          disabled={!editing}
                        />
                      </td>
                      <td>
                        <input
                          className="input input-sm"
                          value={s.package ?? ""}
                          onChange={(e) => updateStudent(i, "package", e.target.value)}
                          disabled={!editing}
                        />
                      </td>
                      <td className="text-xs text-gray-500">
                        {(s.confidence != null
                          ? (s.confidence * 100).toFixed(0)
                          : "—")}%
                      </td>
                      <td className="text-right">
                        <button
                          onClick={() => removeStudent(i)}
                          disabled={!editing}
                          className="text-xs text-red-600 hover:underline"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                  {students.length === 0 && (
                    <tr>
                      <td colSpan={7} className="h-20 text-center text-gray-400">
                        No students extracted
                      </td>
                    </tr>
                  )}
                  <tr>
                    <td colSpan={7}>
                      {editing && (
                        <button
                          onClick={addStudent}
                          className="text-xs text-indigo-600 hover:underline flex items-center gap-1"
                        >
                          <span>+</span> Add student
                        </button>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="space-y-5">
          <div className="rounded-md border border-gray-200 bg-gray-50 p-4">
            <h3 className="text-sm font-semibold mb-2">Confidence &amp; checks</h3>
            <p className="text-sm mb-2">
              Overall confidence:{" "}
              <span className="font-mono font-medium">
                {(item.confidence * 100).toFixed(0)}%
              </span>
            </p>
            {missing.length ? (
              <>
                <p className="text-xs font-semibold text-gray-700 mb-1">
                  Missing fields
                </p>
                <ul className="text-sm text-gray-600 list-disc pl-4 space-y-1">
                  {missing.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="text-sm text-green-600">No missing fields.</p>
            )}
          </div>

          {warnings.length ? (
            <div className="rounded-md border border-amber-100 bg-amber-50 p-4">
              <h3 className="text-sm font-semibold text-amber-800 mb-2">
                Warnings
              </h3>
              <ul className="text-sm text-amber-700 list-disc pl-4 space-y-1">
                {warnings.map((w: string) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="pt-4 flex flex-col sm:flex-row sm:items-end gap-3">
            <button
              onClick={() => onReject(item)}
              disabled={saving}
              className="btn-outline px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              Reject
            </button>
            <button
              onClick={() => onApprove(item)}
              disabled={saving}
              className="btn-primary px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {saving ? "Approving…" : "Approve and add to register"}
            </button>
          </div>
          <p className="text-xs text-gray-500">
            Approved records are written to the database and the Excel register.
          </p>
        </div>
      </div>

      <div className="mt-6 rounded-md border border-gray-200 bg-gray-50 p-4 text-sm">
        <h3 className="font-semibold mb-1">Raw extraction (debug)</h3>
        <pre className="overflow-x-auto text-xs text-gray-500">
          {JSON.stringify(raw, null, 2)}
        </pre>
      </div>
    </Panel>
  );
}
