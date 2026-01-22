import { apiClient } from './client';
import type { Meeting, MeetingListResponse, NextMeetingResponse } from '@/types';

export interface MeetingListParams {
  page?: number;
  page_size?: number;
  status?: string;
}

export interface SetupMeetingsRequest {
  meeting_interval: number;
  meeting_duration: number;
  preferred_time: string;
  preferred_days: number[];
  timezone: string;
}

export interface CreateMeetingRequest {
  scheduled_at: string;
  duration_minutes?: number;
  notes?: string;
}

export const meetingsApi = {
  list: async (params?: MeetingListParams): Promise<MeetingListResponse> => {
    return apiClient.get<MeetingListResponse>('/meetings', params as Record<string, string | number | boolean | undefined>);
  },

  get: async (meetingId: string): Promise<Meeting> => {
    return apiClient.get<Meeting>(`/meetings/${meetingId}`);
  },

  getNext: async (): Promise<NextMeetingResponse> => {
    return apiClient.get<NextMeetingResponse>('/meetings/next');
  },

  create: async (data: CreateMeetingRequest): Promise<Meeting> => {
    return apiClient.post<Meeting>('/meetings', data);
  },

  setup: async (data: SetupMeetingsRequest): Promise<{ message: string; meetings: Meeting[] }> => {
    return apiClient.post<{ message: string; meetings: Meeting[] }>('/meetings/setup', data);
  },

  complete: async (meetingId: string): Promise<Meeting> => {
    return apiClient.post<Meeting>(`/meetings/${meetingId}/complete`);
  },

  cancel: async (meetingId: string): Promise<void> => {
    return apiClient.delete<void>(`/meetings/${meetingId}`);
  },

  reschedule: async (meetingId: string, newTime: string): Promise<Meeting> => {
    return apiClient.patch<Meeting>(`/meetings/${meetingId}/reschedule`, { scheduled_at: newTime });
  },
};
