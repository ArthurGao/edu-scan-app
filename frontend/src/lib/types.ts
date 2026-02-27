export interface SolutionStep {
  step: number;
  description: string;
  formula?: string;
  calculation?: string;
}

export interface FormulaRef {
  id: string;
  name: string;
  latex: string;
}

export interface SolutionResponse {
  question_type: string;
  knowledge_points: string[];
  steps: SolutionStep[];
  final_answer: string;
  explanation?: string;
  tips?: string;
  verification_status?: "verified" | "unverified" | "caution";
  verification_confidence?: number;
}

export interface ScanResponse {
  scan_id: string;
  ocr_text: string;
  solution: SolutionResponse;
  related_formulas: FormulaRef[];
  created_at: string;
}

export interface ScanRecord {
  id: string;
  image_url?: string;
  ocr_text?: string;
  subject?: string;
  difficulty?: string;
  created_at: string;
}

export interface ConversationMessage {
  id: string;
  role: "system" | "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ConversationResponse {
  messages: ConversationMessage[];
  total_messages: number;
}

export interface FollowUpResponse {
  reply: string;
  tokens_used: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

export interface MistakeRecord {
  id: string;
  scan_record: ScanRecord;
  notes?: string;
  mastered: boolean;
  review_count: number;
  next_review_at?: string;
  created_at: string;
}

export interface Formula {
  id: string;
  subject: string;
  category?: string;
  name: string;
  latex: string;
  description?: string;
  grade_levels: string[];
}

export interface FormulaDetail extends Formula {
  keywords: string[];
  related_formulas: Formula[];
}
