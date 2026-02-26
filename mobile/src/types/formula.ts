import { Subject } from './scan';

export interface Formula {
  id: string;
  subject: Subject;
  category?: string;
  name: string;
  latex: string;
  description?: string;
  gradeLevels: string[];
}

export interface FormulaDetail extends Formula {
  keywords: string[];
  relatedFormulas: Formula[];
}

export interface FormulaSearchParams {
  subject?: Subject;
  category?: string;
  gradeLevel?: string;
  keyword?: string;
  page?: number;
  limit?: number;
}
