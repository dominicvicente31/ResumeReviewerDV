import axios from "axios";
import type {
  JobProfile,
  Submission,
  SubmissionListItem,
  TokenResponse,
  User,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: BASE_URL });

// Attach token on every request
api.interceptors.request.use((config) => {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401, clear tokens and redirect to login
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  signup: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/signup", { email, password }),

  login: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { email, password }),

  logout: () => api.post("/auth/logout"),

  refresh: (refresh_token: string) =>
    api.post<TokenResponse>("/auth/refresh", { refresh_token }),

  me: () => api.get<User>("/auth/me"),

  verifyEmail: (token: string) =>
    api.get<{ detail: string }>(`/auth/verify-email?token=${token}`),

  resendVerification: (email: string) =>
    api.post("/auth/resend-verification", { email }),
};

// ── Profiles ─────────────────────────────────────────────────────────────────

export const profilesApi = {
  list: () => api.get<JobProfile[]>("/profiles"),

  get: (id: number) => api.get<JobProfile>(`/profiles/${id}`),

  create: (data: {
    title: string;
    description: string;
    requirements: { text: string; weight: number; must_have: boolean }[];
  }) => api.post<JobProfile>("/profiles", data),

  update: (
    id: number,
    data: { title?: string; description?: string; is_active?: boolean }
  ) => api.put<JobProfile>(`/profiles/${id}`, data),

  patchRequirement: (
    profileId: number,
    reqId: number,
    data: { weight?: number; must_have?: boolean }
  ) => api.patch(`/profiles/${profileId}/requirements/${reqId}`, data),
};

// ── Submissions ───────────────────────────────────────────────────────────────

export const submissionsApi = {
  submit: (profileId: number, file: File) => {
    const form = new FormData();
    form.append("profile_id", String(profileId));
    form.append("file", file);
    return api.post<Submission>("/submissions", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  get: (id: number) => api.get<Submission>(`/submissions/${id}`),

  mine: (skip = 0, limit = 50) =>
    api.get<SubmissionListItem[]>("/submissions/me", {
      params: { skip, limit },
    }),

  all: (skip = 0, limit = 100) =>
    api.get<SubmissionListItem[]>("/submissions", { params: { skip, limit } }),

  rescore: (id: number) =>
    api.post<Submission>(`/submissions/${id}/rescore`),
};

// ── Admin ─────────────────────────────────────────────────────────────────────

export const adminApi = {
  listUsers: () => api.get<User[]>("/admin/users"),
  createUser: (email: string, password: string, role: "user" | "admin") =>
    api.post<User>("/admin/users", { email, password, role }),
};
