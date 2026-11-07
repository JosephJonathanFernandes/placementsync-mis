export interface ExtractedStudent {
  name: string;
  registration_number?: string | null;
  branch?: string | null;
  job_role?: string | null;
  package?: string | null;
  confidence?: number;
}

export interface EmailOut {
  id: number;
  email_id: string;
  subject: string | null;
  sender: string | null;
  source: string;
  is_processed: boolean;
  received_at: string | null;
  created_at: string;
}

export interface EmailUploadResult {
  email_id: number;
  external_email_id: string;
  subject: string | null;
  sender: string | null;
  body_preview: string | null;
  message: string;
}

export interface ExtractionResultOut {
  id: number;
  email_id: number;
  company_name: string | null;
  confidence: number; // 0 - 1
  review_status: "pending" | "approved" | "rejected";
  extracted_students: ExtractedStudent[];
  raw_extraction: Record<string, unknown>;
  missing_fields: string[];
  warnings: string[];
  created_at: string;
}

export interface ExtractionResultWithEmail extends ExtractionResultOut {
  email_subject: string | null;
  email_sender: string | null;
  email_body: string | null;
}

export interface ApprovalAction {
  action: "approve" | "reject";
  edited_students?: ExtractedStudent[];
  edited_company?: string;
  notes?: string;
}

export interface PlacementRecordWithDetails {
  id: number;
  student_id: number;
  company_id: number;
  job_role: string | null;
  package: string | null;
  selection_date: string | null;
  status: string;
  approval_status: string;
  email_id: number | null;
  extraction_result_id: number | null;
  approved_at: string | null;
  approved_by: string | null;
  created_at: string;
  updated_at: string;
  student_name: string | null;
  student_registration_number: string | null;
  student_branch: string | null;
  company_name: string | null;
}

export interface DashboardStats {
  total_selected_students: number;
  total_unique_placed_students: number;
  total_companies: number;
  pending_email_reviews: number;
  highest_package: number | null;
  average_package: number | null;
  branch_statistics: Array<{ branch: string; count: number }>;
  company_statistics: Array<{ company: string; count: number }>;
  package_distribution: Array<{ range: string; count: number }>;
}

export interface GmailConnectionStatus {
  connected: boolean;
  email_address: string | null;
  scopes: string[];
  token_expiry: string | null;
}

export interface GmailProcessSummary {
  fetched: number;
  stored: number;
  skipped_duplicate: number;
  classified_selection: number;
  created_review_results: number;
  attachment_errors: number;
  errors: number;
}

export interface GmailLabel {
  id: string;
  name: string;
  type: string;
}

export interface GmailMessageSummary {
  id: string;
  thread_id: string;
  snippet: string;
}
