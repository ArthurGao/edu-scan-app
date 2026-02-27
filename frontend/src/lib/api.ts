import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

export default api;

// Scan
export async function solveImage(
  file: File,
  subject?: string,
  gradeLevel?: string
) {
  const formData = new FormData();
  formData.append("image", file);
  if (subject) formData.append("subject", subject);
  if (gradeLevel) formData.append("grade_level", gradeLevel);
  const res = await api.post("/scan/solve-guest", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function solveText(
  text: string,
  subject?: string,
  gradeLevel?: string
) {
  const formData = new FormData();
  formData.append("text", text);
  if (subject) formData.append("subject", subject);
  if (gradeLevel) formData.append("grade_level", gradeLevel);
  const res = await api.post("/scan/solve-guest", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function getScanResult(scanId: string) {
  const res = await api.get(`/scan/${scanId}`);
  return res.data;
}

export async function getConversation(scanId: string) {
  const res = await api.get(`/scan/${scanId}/conversation`);
  return res.data;
}

export async function sendFollowUp(scanId: string, message: string) {
  const res = await api.post(`/scan/${scanId}/followup`, { message });
  return res.data;
}

// History
export async function getHistory(params?: {
  subject?: string;
  page?: number;
  limit?: number;
}) {
  const res = await api.get("/history", { params });
  return res.data;
}

export async function deleteHistoryItem(scanId: string) {
  const res = await api.delete(`/history/${scanId}`);
  return res.data;
}

// Mistakes
export async function getMistakes(params?: {
  subject?: string;
  mastered?: boolean;
  page?: number;
  limit?: number;
}) {
  const res = await api.get("/mistakes", { params });
  return res.data;
}

export async function addToMistakes(scanId: string, notes?: string) {
  const res = await api.post("/mistakes", { scan_id: scanId, notes });
  return res.data;
}

export async function updateMistake(
  id: string,
  data: { notes?: string; mastered?: boolean }
) {
  const res = await api.patch(`/mistakes/${id}`, data);
  return res.data;
}

export async function deleteMistake(id: string) {
  const res = await api.delete(`/mistakes/${id}`);
  return res.data;
}

// Formulas
export async function getFormulas(params?: {
  subject?: string;
  category?: string;
  keyword?: string;
  page?: number;
  limit?: number;
}) {
  const res = await api.get("/formulas", { params });
  return res.data;
}

export async function getFormula(id: string) {
  const res = await api.get(`/formulas/${id}`);
  return res.data;
}
