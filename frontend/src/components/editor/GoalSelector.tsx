'use client';

import { useState } from 'react';
import { useGoals, useGoalMutations, useTemplates } from '@/hooks/useGoals';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus, Target, FileText, Loader2 } from 'lucide-react';

interface GoalSelectorProps {
  value: string | null;
  onChange: (goalId: string | null) => void;
}

export function GoalSelector({ value, onChange }: GoalSelectorProps) {
  const { data: goalsData, isLoading } = useGoals({ page_size: 50, sort_by: 'updated_at', sort_order: 'desc' });
  useTemplates(); // Prefetch templates
  const { createGoal, createFromTemplate } = useGoalMutations();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [templateType, setTemplateType] = useState<string>('custom');

  const handleCreate = async () => {
    if (!title.trim()) return;

    try {
      let newGoal;
      if (templateType === 'custom') {
        newGoal = await createGoal.mutateAsync({ title, template_type: 'custom' });
      } else {
        newGoal = await createFromTemplate.mutateAsync({ template_type: templateType, title });
      }

      if (newGoal) {
        onChange(newGoal.id);
      }
      setDialogOpen(false);
      setTitle('');
      setTemplateType('custom');
    } catch {
      // Error handled by mutation
    }
  };

  const goals = goalsData?.goals || [];

  return (
    <div className="flex items-center gap-2">
      <Select
        value={value || ''}
        onValueChange={(v) => onChange(v || null)}
      >
        <SelectTrigger className="w-[200px]">
          <SelectValue placeholder="Select a goal">
            {isLoading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading...
              </span>
            ) : value ? (
              <span className="flex items-center gap-2">
                <Target className="h-4 w-4" />
                {goals.find((g) => g.id === value)?.title || 'Select goal'}
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Select goal
              </span>
            )}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {goals.length === 0 ? (
            <div className="p-2 text-sm text-muted-foreground text-center">
              No goals yet
            </div>
          ) : (
            goals.map((goal) => (
              <SelectItem key={goal.id} value={goal.id}>
                <span className="flex items-center gap-2">
                  <Target className="h-4 w-4" />
                  {goal.title}
                </span>
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogTrigger asChild>
          <Button size="icon" variant="outline">
            <Plus className="h-4 w-4" />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Goal</DialogTitle>
            <DialogDescription>
              Start fresh or use a template to structure your goal.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="title">Goal Title</Label>
              <Input
                id="title"
                placeholder="Enter your goal title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Template</Label>
              <div className="grid grid-cols-3 gap-2">
                <Button
                  type="button"
                  variant={templateType === 'custom' ? 'default' : 'outline'}
                  className="h-auto py-3 flex flex-col"
                  onClick={() => setTemplateType('custom')}
                >
                  <FileText className="h-5 w-5 mb-1" />
                  <span className="text-xs">Custom</span>
                </Button>
                <Button
                  type="button"
                  variant={templateType === 'smart' ? 'default' : 'outline'}
                  className="h-auto py-3 flex flex-col"
                  onClick={() => setTemplateType('smart')}
                >
                  <Target className="h-5 w-5 mb-1" />
                  <span className="text-xs">SMART</span>
                </Button>
                <Button
                  type="button"
                  variant={templateType === 'okr' ? 'default' : 'outline'}
                  className="h-auto py-3 flex flex-col"
                  onClick={() => setTemplateType('okr')}
                >
                  <Target className="h-5 w-5 mb-1" />
                  <span className="text-xs">OKR</span>
                </Button>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!title.trim() || createGoal.isPending || createFromTemplate.isPending}
            >
              {(createGoal.isPending || createFromTemplate.isPending) && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Create Goal
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
