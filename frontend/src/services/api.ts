import axios, { AxiosInstance } from "axios";
import type {
  EmailOut,
  EmailUploadResult,
  ExtractionResultWithEmail,
  ExtractionResultOut,
  ApprovalAction,
  PlacementRecordWithDetails,
  DashboardStats,
  GmailConnectionStatus,
  GmailProcessSummary,
  GmailLabel,
  GmailMessageSummary,
  AuditLogOut,
} from "@/types";

const api: AxiosInstance = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export const emailService = {
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post<EmailUploadResult>("/emails/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  list: () => api.get<EmailOut[]>("/emails"),
  get: (id: number) => api.get<EmailOut>(`/emails/${id}`),
};

export const extractionService = {
  run: (emailId: number) =>
    api.post<ExtractionResultOut>(`/extraction/run/${emailId}`),
  listPending: () => api.get<ExtractionResultWithEmail[]>("/extraction/pending"),
  get: (id: number) =>
    api.get<ExtractionResultWithEmail>(`/extraction/${id}`),
  approve: (id: number, action: ApprovalAction) =>
    api.post<ExtractionResultOut>(`/extraction/${id}/approve`, action),
  reject: (id: number, action: ApprovalAction) =>
    api.post<ExtractionResultOut>(`/extraction/${id}/reject`, action),
};

export const recordsService = {
  list: (params?: {
    company?: string;
    branch?: string;
    status?: string;
  }) => api.get<PlacementRecordWithDetails[]>("/records", { params }),
  stats: (params?: {
    company?: string;
    branch?: string;
    status?: string;
    date_from?: string;
    date_to?: string;
  }) => api.get<DashboardStats>("/records/stats", { params }),
};

export const excelService = {
  export: () => api.get("/excel/export", { responseType: "blob" }),
  download: () => api.get("/excel/download", { responseType: "blob" }),
};

export const gmailAuthService = {
  authorize: () => api.get<{ authorization_url: string; state: string }>("/auth/gmail/authorize"),
  status: () => api.get<GmailConnectionStatus>("/auth/gmail/status"),
  disconnect: () => api.post<{ message: string }>("/auth/gmail/disconnect"),
};

export const gmailService = {
  listMessages: (params?: {
    query?: string;
    max_results?: number;
    label_ids?: string;
  }) => api.get<{ query: string; count: number; messages: GmailMessageSummary[] }>("/gmail/messages", { params }),
  listLabels: () => api.get<{ labels: GmailLabel[] }>("/gmail/labels"),
  process: (params?: {
    query?: string;
    max_results?: number;
    label_ids?: string;
  }) =>
    api.post<{ message: string; summary: GmailProcessSummary }>(
      "/gmail/process",
      {},
      { params }
    ),
};

export const auditService = {
  list: (params?: {
    skip?: number;
    limit?: number;
    table_name?: string;
    action?: string;
  }) => api.get<AuditLogOut[]>("/audit", { params }),
  summary: () => api.get<Record<string, Record<string, number>>>("/audit/summary"),
};

export const backupService = {
  database: () => api.post<Blob>("/backup/database", {}, { responseType: "blob" }),
  excel: () => api.post<Blob>("/backup/excel", {}, { responseType: "blob" }),
  restore: () => api.post<{ message: string; steps: string[]; note: string }>(
    "/backup/restore",
    {}
  ),
};

export default api;
