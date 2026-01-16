import { apiClient } from './client';
import type { Goal, GoalListResponse, CreateGoalRequest, UpdateGoalRequest, Template } from '@/types';

export interface GoalListParams {
  page?: number;
  page_size?: number;
  phase?: string;
  template_type?: string;
  search?: string;
}

export interface GoalStatistics {
  total: number;
  by_phase: Record<string, number>;
  by_template: Record<string, number>;
  completion_rate: number;
}

export const goalsApi = {
  list: async (params?: GoalListParams): Promise<GoalListResponse> => {
    return apiClient.get<GoalListResponse>('/goals', params as Record<string, string | number | boolean | undefined>);
  },

  get: async (goalId: string): Promise<Goal> => {
    return apiClient.get<Goal>(`/goals/${goalId}`);
  },

  create: async (data: CreateGoalRequest): Promise<Goal> => {
    return apiClient.post<Goal>('/goals', data);
  },

  update: async (goalId: string, data: UpdateGoalRequest): Promise<Goal> => {
    return apiClient.put<Goal>(`/goals/${goalId}`, data);
  },

  updatePhase: async (goalId: string, phase: string): Promise<Goal> => {
    return apiClient.patch<Goal>(`/goals/${goalId}/phase`, { phase });
  },

  delete: async (goalId: string): Promise<void> => {
    return apiClient.delete<void>(`/goals/${goalId}`);
  },

  getStatistics: async (): Promise<GoalStatistics> => {
    return apiClient.get<GoalStatistics>('/goals/statistics');
  },

  getTemplates: async (): Promise<Template[]> => {
    return apiClient.get<Template[]>('/goals/templates');
  },

  createFromTemplate: async (data: { template_type: string; title: string }): Promise<Goal> => {
    return apiClient.post<Goal>('/goals/from-template', data);
  },

  export: async (goalId: string): Promise<Blob> => {
    return apiClient.getBlob(`/goals/${goalId}/export`);
  },
};
