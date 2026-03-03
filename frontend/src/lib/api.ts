import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

let getTokenFn: (() => Promise<string | null>) | null = null;

export function setAuthTokenProvider(fn: () => Promise<string | null>) {
  getTokenFn = fn;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(async (config) => {
  if (getTokenFn) {
    try {
      const token = await getTokenFn();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // Silently fail - user may not be authenticated
    }
  }
  return config;
});

export default api;

// OCR — extract text only
export async function extractText(file: File): Promise<{ ocr_text: string }> {
  const formData = new FormData();
  formData.append("image", file);
  const res = await api.post("/scan/extract-text", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

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

export async function solveTextStream(
  text: string,
  onEvent: (event: string, data: unknown) => void,
  subject?: string,
  gradeLevel?: string
): Promise<void> {
  const formData = new FormData();
  formData.append("text", text);
  if (subject) formData.append("subject", subject);
  if (gradeLevel) formData.append("grade_level", gradeLevel);

  const headers: Record<string, string> = {};
  if (getTokenFn) {
    try {
      const token = await getTokenFn();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    } catch {
      // not authenticated
    }
  }

  const response = await fetch(`${API_BASE_URL}/scan/solve-guest-stream`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ") && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent(currentEvent, data);
        } catch {
          // skip malformed data
        }
        currentEvent = "";
      }
    }
  }
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

export async function saveFormula(data: {
  name: string;
  latex: string;
  subject?: string;
  description?: string;
}) {
  const res = await api.post("/formulas", data);
  return res.data;
}
