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
  UserOut,
  UserCreate,
  UserUpdate,
  LoginRequest,
  Token,
} from "@/types";

const api: AxiosInstance = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// ---------------------------------------------------------------------------
// Auth token helpers
// ---------------------------------------------------------------------------

const TOKEN_KEY = "placementsync_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

// Request interceptor: attach auth token to every request
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 by clearing token and redirecting to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      removeToken();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Auth service
// ---------------------------------------------------------------------------

export const authService = {
  login: (data: LoginRequest) =>
    api.post<Token>("/auth/login", data),

  register: (data: UserCreate) =>
    api.post<UserOut>("/auth/register", data),

  me: () => api.get<UserOut>("/auth/me"),

  logout: () => api.post<{ message: string }>("/auth/logout"),

  listUsers: () => api.get<UserOut[]>("/auth/users"),

  getUser: (id: number) => api.get<UserOut>(`/auth/users/${id}`),

  updateUser: (id: number, data: UserUpdate) =>
    api.put<UserOut>(`/auth/users/${id}`, data),

  deleteUser: (id: number) => api.delete<{ message: string }>(`/auth/users/${id}`),
};

// ---------------------------------------------------------------------------
// Email service
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Extraction service
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Records service
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Excel service
// ---------------------------------------------------------------------------

export const excelService = {
  export: () => api.get("/excel/export", { responseType: "blob" }),
  download: () => api.get("/excel/download", { responseType: "blob" }),
};

// ---------------------------------------------------------------------------
// Gmail auth service
// ---------------------------------------------------------------------------

export const gmailAuthService = {
  authorize: () =>
    api.get<{ authorization_url: string; state: string }>(
      "/auth/gmail/authorize"
    ),
  status: () => api.get<GmailConnectionStatus>("/auth/gmail/status"),
  disconnect: () => api.post<{ message: string }>("/auth/gmail/disconnect"),
};

// ---------------------------------------------------------------------------
// Gmail service
// ---------------------------------------------------------------------------

export const gmailService = {
  listMessages: (params?: {
    query?: string;
    max_results?: number;
    label_ids?: string;
  }) =>
    api.get<{
      query: string;
      count: number;
      messages: GmailMessageSummary[];
    }>("/gmail/messages", { params }),
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

// ---------------------------------------------------------------------------
// Audit service
// ---------------------------------------------------------------------------

export const auditService = {
  list: (params?: {
    skip?: number;
    limit?: number;
    table_name?: string;
    action?: string;
  }) => api.get<AuditLogOut[]>("/audit", { params }),
  summary: () =>
    api.get<Record<string, Record<string, number>>>("/audit/summary"),
};

// ---------------------------------------------------------------------------
// Backup service
// ---------------------------------------------------------------------------

export const backupService = {
  database: () =>
    api.post<Blob>("/backup/database", {}, { responseType: "blob" }),
  excel: () => api.post<Blob>("/backup/excel", {}, { responseType: "blob" }),
  restore: () =>
    api.post<{ message: string; steps: string[]; note: string }>(
      "/backup/restore",
      {}
    ),
};

export default api;
