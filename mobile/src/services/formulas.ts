import apiClient from './api';
import { Formula, FormulaDetail, FormulaSearchParams, PaginatedResponse } from '@/types';

export const formulasService = {
  async getFormulas(params: FormulaSearchParams = {}): Promise<PaginatedResponse<Formula>> {
    const response = await apiClient.get<PaginatedResponse<Formula>>('/formulas', {
      params: {
        subject: params.subject,
        category: params.category,
        grade_level: params.gradeLevel,
        keyword: params.keyword,
        page: params.page || 1,
        limit: params.limit || 20,
      },
    });
    return response.data;
  },

  async getFormula(formulaId: string): Promise<FormulaDetail> {
    const response = await apiClient.get<FormulaDetail>(`/formulas/${formulaId}`);
    return response.data;
  },
};
