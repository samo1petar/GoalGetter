'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { goalsApi, type GoalListParams } from '@/lib/api/goals';
import type { CreateGoalRequest, UpdateGoalRequest } from '@/types';
import { toast } from 'sonner';

export function useGoals(params?: GoalListParams) {
  return useQuery({
    queryKey: ['goals', params],
    queryFn: () => goalsApi.list(params),
  });
}

export function useGoal(goalId: string | null) {
  return useQuery({
    queryKey: ['goal', goalId],
    queryFn: () => (goalId ? goalsApi.get(goalId) : null),
    enabled: !!goalId,
  });
}

export function useGoalStatistics() {
  return useQuery({
    queryKey: ['goals', 'statistics'],
    queryFn: goalsApi.getStatistics,
  });
}

export function useTemplates() {
  return useQuery({
    queryKey: ['templates'],
    queryFn: goalsApi.getTemplates,
  });
}

export function useGoalMutations() {
  const queryClient = useQueryClient();

  const createGoal = useMutation({
    mutationFn: (data: CreateGoalRequest) => goalsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      toast.success('Goal created successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create goal');
    },
  });

  const updateGoal = useMutation({
    mutationFn: ({ goalId, data }: { goalId: string; data: UpdateGoalRequest }) =>
      goalsApi.update(goalId, data),
    onSuccess: (_, { goalId }) => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['goal', goalId] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update goal');
    },
  });

  const updateGoalPhase = useMutation({
    mutationFn: ({ goalId, phase }: { goalId: string; phase: string }) =>
      goalsApi.updatePhase(goalId, phase),
    onSuccess: (_, { goalId }) => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['goal', goalId] });
      toast.success('Goal phase updated');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update phase');
    },
  });

  const deleteGoal = useMutation({
    mutationFn: (goalId: string) => goalsApi.delete(goalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      toast.success('Goal deleted');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete goal');
    },
  });

  const createFromTemplate = useMutation({
    mutationFn: (data: { template_type: string; title: string }) =>
      goalsApi.createFromTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      toast.success('Goal created from template');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create from template');
    },
  });

  const exportGoal = async (goalId: string, title: string) => {
    try {
      const blob = await goalsApi.export(goalId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.replace(/[^a-z0-9]/gi, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Goal exported successfully');
    } catch {
      toast.error('Failed to export goal');
    }
  };

  return {
    createGoal,
    updateGoal,
    updateGoalPhase,
    deleteGoal,
    createFromTemplate,
    exportGoal,
  };
}
