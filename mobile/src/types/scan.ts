export type AIProvider = 'claude' | 'gpt' | 'gemini';

export type Subject =
  | 'math'
  | 'physics'
  | 'chemistry'
  | 'biology'
  | 'english'
  | 'chinese'
  | 'history'
  | 'geography'
  | 'other';

export type Difficulty = 'easy' | 'medium' | 'hard';

export interface SolveRequest {
  image: {
    uri: string;
    type: string;
    name: string;
  };
  subject?: Subject;
  aiProvider?: AIProvider;
  gradeLevel?: string;
}

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

export interface Solution {
  questionType: string;
  knowledgePoints: string[];
  steps: SolutionStep[];
  finalAnswer: string;
  explanation?: string;
  tips?: string;
}

export interface ScanResult {
  scanId: string;
  ocrText: string;
  solution: Solution;
  relatedFormulas: FormulaRef[];
  createdAt: string;
}

export interface ScanRecord {
  id: string;
  imageUrl: string;
  ocrText?: string;
  subject?: Subject;
  difficulty?: Difficulty;
  createdAt: string;
}

export interface ScanState {
  isScanning: boolean;
  isProcessing: boolean;
  currentScan: ScanResult | null;
  error: string | null;
}
