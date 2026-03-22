import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1",
  timeout: 120_000,
});

let tokenProvider: (() => Promise<string | null>) | null = null;

export function setTokenProvider(fn: () => Promise<string | null>) {
  tokenProvider = fn;
}

api.interceptors.request.use(async (config) => {
  if (tokenProvider) {
    const token = await tokenProvider();
    console.log("[API] token present:", !!token, token?.slice(0, 20));
    if (token) config.headers.Authorization = `Bearer ${token}`;
  } else {
    console.log("[API] no tokenProvider set");
  }
  return config;
});

export default api;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

export interface StatsOverview {
  total_users: number;
  active_today: number;
  questions_today: number;
  tier_distribution: Record<string, number>;
}

export interface DailyStat {
  date: string;
  active_users: number;
  questions: number;
}

export interface UserInfo {
  id: number;
  clerk_id?: string;
  email: string;
  nickname?: string;
  avatar_url?: string;
  grade_level?: string;
  role: string;
  tier_id?: number;
  is_active: boolean;
  created_at: string;
  today_usage?: number;
}

export interface ExamPaper {
  id: string;
  title: string;
  year: number;
  subject: string;
  exam_code: string;
  paper_type: string;
  language: string;
  total_questions: number;
  created_at: string;
}

export interface PracticeQuestion {
  id: string;
  exam_paper_id: string;
  question_number: string;
  sub_question: string;
  question_text: string;
  question_type: string | null;
  has_image: boolean;
  image_url: string | null;
  order_index: number;
  correct_answer: string | null;
  accepted_answers: string[] | null;
  answer_explanation: string | null;
  marks: string | null;
  outcome: number | null;
}

export interface ExamUploadResponse {
  exam_paper: ExamPaper;
  total_questions_parsed: number;
  questions: PracticeQuestion[];
}

export interface CrawlResponse {
  url: string;
  total_pdfs_discovered: number;
  total_papers_imported: number;
  total_questions_parsed: number;
  total_skipped: number;
  papers: { title: string; year: number; total_questions: number; exam_paper_id: string }[];
  skipped: string[];
  failed: string[];
  errors: string[];
}

// ---------------------------------------------------------------------------
// Admin Stats
// ---------------------------------------------------------------------------

export async function getStatsOverview(): Promise<StatsOverview> {
  return (await api.get("/admin/stats/overview")).data;
}

export async function getDailyStats(days = 14): Promise<DailyStat[]> {
  return (await api.get("/admin/stats/daily", { params: { days } })).data;
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export async function getUsers(params?: {
  page?: number;
  limit?: number;
  search?: string;
  role?: string;
  is_active?: boolean;
}): Promise<PaginatedResponse<UserInfo>> {
  // Backend uses page_size instead of limit, and doesn't return pages/limit
  const backendParams = {
    ...params,
    page_size: params?.limit,
    limit: undefined,
  };
  const raw = (await api.get("/admin/users", { params: backendParams })).data;
  const pageSize = raw.page_size || params?.limit || 20;
  return {
    items: raw.items,
    total: raw.total,
    page: raw.page,
    limit: pageSize,
    pages: Math.max(1, Math.ceil(raw.total / pageSize)),
  };
}

export async function updateUser(
  userId: number,
  data: { role?: string; is_active?: boolean },
): Promise<UserInfo> {
  return (await api.patch(`/admin/users/${userId}`, data)).data;
}

// ---------------------------------------------------------------------------
// Exam Papers
// ---------------------------------------------------------------------------

export async function getExamPapers(params?: {
  year?: number;
  subject?: string;
  language?: string;
  page?: number;
  limit?: number;
}): Promise<PaginatedResponse<ExamPaper>> {
  return (await api.get("/exams", { params })).data;
}

export async function uploadExamPdf(formData: FormData): Promise<ExamUploadResponse> {
  return (await api.post("/exams/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })).data;
}

export async function crawlExams(data: {
  url: string;
  language?: string;
  subject?: string;
  exam_code?: string;
}): Promise<CrawlResponse> {
  return (await api.post("/exams/crawl", data)).data;
}

export async function deleteExamPaper(examId: string): Promise<void> {
  await api.delete(`/exams/${examId}`);
}

export async function uploadSchedule(examId: string, file: File): Promise<{
  exam_id: number;
  title: string;
  total_questions: number;
  answers_updated: number;
  answers_parsed: number;
}> {
  const fd = new FormData();
  fd.append("schedule_pdf", file);
  return (await api.post(`/exams/${examId}/schedule`, fd, {
    headers: { "Content-Type": "multipart/form-data" },
  })).data;
}

// ---------------------------------------------------------------------------
// Questions (admin view — includes answers)
// ---------------------------------------------------------------------------

export async function getQuestionsAdmin(
  examId: string,
  params?: {
    question_type?: string;
    question_number?: string;
    page?: number;
    limit?: number;
  },
): Promise<PaginatedResponse<PracticeQuestion>> {
  return (await api.get(`/exams/${examId}/questions/admin`, { params })).data;
}
