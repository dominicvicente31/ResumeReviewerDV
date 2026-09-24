export type Role = "user" | "admin";

export interface User {
  id: string;
  email: string;
  role: Role;
  is_verified: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface JobRequirement {
  id: number;
  text: string;
  weight: number;
  must_have: boolean;
}

export interface JobProfile {
  id: number;
  title: string;
  description: string;
  is_active: boolean;
  created_at: string;
  requirements: JobRequirement[];
}

export type Verdict = "met" | "partial" | "not_met";
export type SubmissionStatus = "pending" | "processing" | "completed" | "failed";

export interface SubmissionResult {
  requirement_id: number;
  verdict: Verdict;
  evidence: string;
  rationale: string;
  evidence_verified: boolean;
  confidence: number;
}

export interface Submission {
  id: number;
  user_id: string;
  job_profile_id: number;
  resume_filename: string;
  status: SubmissionStatus;
  overall_score: number | null;
  capped_by_must_have: boolean;
  created_at: string;
  results: SubmissionResult[];
}

export interface SubmissionListItem {
  id: number;
  job_profile_id: number;
  status: SubmissionStatus;
  overall_score: number | null;
  capped_by_must_have: boolean;
  created_at: string;
}
