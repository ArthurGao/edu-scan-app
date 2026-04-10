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

export interface SSEStageEvent {
  stage: string;
  message: string;
}

export interface SSEOcrResultEvent {
  ocr_text: string;
}

export interface SSEErrorEvent {
  message: string;
}

export type SSEEvent =
  | { event: "stage"; data: SSEStageEvent }
  | { event: "ocr_result"; data: SSEOcrResultEvent }
  | { event: "complete"; data: ScanResponse }
  | { event: "error"; data: SSEErrorEvent };

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

export interface ExamPaper {
  id: string;
  title: string;
  year: number;
  subject: string;
  level: number;
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
  options: string[] | null;
  has_image: boolean;
  image_url: string | null;
  order_index: number;
}

export interface QuestionAnswer {
  id: string;
  correct_answer: string | null;
  accepted_answers: string[] | null;
  answer_explanation: string | null;
  marks: string | null;
  outcome: number | null;
}

// Practice generation types
export interface PracticeQuestionGenerated {
  id: string;
  question_text: string;
  question_type: string | null;
  difficulty: string | null;
  difficulty_offset: number;
  knowledge_points: string[] | null;
  marks: string | null;
  answered: boolean;
  is_correct: boolean | null;
}

export interface GeneratePracticeResponse {
  status: "ready" | "generating" | "error" | "empty";
  scan_id: string;
  questions: PracticeQuestionGenerated[];
  message?: string;
}

export interface SubmitPracticeAnswerResponse {
  is_correct: boolean;
  grading_method: string;
  correct_answer: string | null;
  accepted_answers: string[] | null;
  answer_explanation: string | null;
  ai_feedback: string | null;
  knowledge_points: string[] | null;
}
