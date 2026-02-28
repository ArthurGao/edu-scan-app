import api from "./api";

// --- Types ---

export interface TierInfo {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  daily_question_limit: number;
  allowed_ai_models: string[];
  features: Record<string, boolean | number>;
  max_image_size_mb: number;
  is_default: boolean;
  is_active: boolean;
  sort_order: number;
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
  tier?: TierInfo;
  today_usage?: number;
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

export interface SystemSettingItem {
  id: number;
  key: string;
  value: unknown;
  description?: string;
  updated_at: string;
}

// --- Stats ---

export async function getStatsOverview(): Promise<StatsOverview> {
  const res = await api.get("/admin/stats/overview");
  return res.data;
}

export async function getDailyStats(days?: number): Promise<DailyStat[]> {
  const res = await api.get("/admin/stats/daily", { params: { days } });
  return res.data;
}

// --- Users ---

export async function getUsers(params?: {
  page?: number;
  limit?: number;
  search?: string;
  role?: string;
  tier_id?: number;
  is_active?: boolean;
}) {
  const res = await api.get("/admin/users", { params });
  return res.data;
}

export async function getUser(userId: number): Promise<UserInfo> {
  const res = await api.get(`/admin/users/${userId}`);
  return res.data;
}

export async function updateUser(
  userId: number,
  data: { role?: string; tier_id?: number; is_active?: boolean }
) {
  const res = await api.patch(`/admin/users/${userId}`, data);
  return res.data;
}

// --- Tiers ---

export async function getTiers(): Promise<(TierInfo & { user_count?: number })[]> {
  const res = await api.get("/admin/tiers");
  return res.data;
}

export async function createTier(data: Partial<TierInfo>) {
  const res = await api.post("/admin/tiers", data);
  return res.data;
}

export async function updateTier(tierId: number, data: Partial<TierInfo>) {
  const res = await api.patch(`/admin/tiers/${tierId}`, data);
  return res.data;
}

export async function deleteTier(tierId: number) {
  const res = await api.delete(`/admin/tiers/${tierId}`);
  return res.data;
}

// --- Settings ---

export async function getSettings(): Promise<SystemSettingItem[]> {
  const res = await api.get("/admin/settings");
  return res.data;
}

export async function updateSettings(settings: Record<string, unknown>) {
  const res = await api.patch("/admin/settings", settings);
  return res.data;
}
