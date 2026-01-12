'use client';

import { useState } from 'react';
import { useGoals, useGoalMutations } from '@/hooks/useGoals';
import { useUIStore } from '@/stores/uiStore';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Target,
  Plus,
  Search,
  Trash2,
  Download,
  ExternalLink,
  Loader2,
} from 'lucide-react';

export default function GoalsPage() {
  const router = useRouter();
  const { setActiveGoalId } = useUIStore();
  const [search, setSearch] = useState('');
  const [phaseFilter, setPhaseFilter] = useState<string>('all');

  const { data, isLoading } = useGoals({
    search: search || undefined,
    phase: phaseFilter !== 'all' ? phaseFilter : undefined,
    sort_by: 'updated_at',
    sort_order: 'desc',
  });

  const { deleteGoal, exportGoal } = useGoalMutations();

  const goals = data?.goals || [];

  const phaseColors: Record<string, string> = {
    draft: 'bg-yellow-100 text-yellow-800',
    active: 'bg-green-100 text-green-800',
    completed: 'bg-blue-100 text-blue-800',
    archived: 'bg-gray-100 text-gray-800',
  };

  const handleOpenGoal = (goalId: string) => {
    setActiveGoalId(goalId);
    router.push('/app');
  };

  const handleDelete = (goalId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this goal?')) {
      deleteGoal.mutate(goalId);
    }
  };

  const handleExport = (goal: { id: string; title: string }, e: React.MouseEvent) => {
    e.stopPropagation();
    exportGoal(goal.id, goal.title);
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Goals</h1>
          <p className="text-muted-foreground">Manage and track all your goals</p>
        </div>
        <Button onClick={() => router.push('/app')}>
          <Plus className="h-4 w-4 mr-2" />
          New Goal
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search goals..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={phaseFilter} onValueChange={setPhaseFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="All phases" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All phases</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Goals List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : goals.length === 0 ? (
        <Card className="text-center py-12">
          <CardContent>
            <Target className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No goals found</h3>
            <p className="text-muted-foreground mb-4">
              {search || phaseFilter !== 'all'
                ? 'Try adjusting your filters'
                : 'Create your first goal to get started'}
            </p>
            {!search && phaseFilter === 'all' && (
              <Button onClick={() => router.push('/app')}>
                <Plus className="h-4 w-4 mr-2" />
                Create Goal
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {goals.map((goal) => (
            <Card
              key={goal.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => handleOpenGoal(goal.id)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      {goal.title}
                      <Badge className={phaseColors[goal.phase]} variant="secondary">
                        {goal.phase}
                      </Badge>
                    </CardTitle>
                    <CardDescription>
                      {goal.template_type.toUpperCase()} template
                      {goal.metadata.deadline && (
                        <> &middot; Due {new Date(goal.metadata.deadline).toLocaleDateString()}</>
                      )}
                    </CardDescription>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => handleExport(goal, e)}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => handleDelete(goal.id, e)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                    <Button variant="ghost" size="icon">
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              {goal.metadata.tags && goal.metadata.tags.length > 0 && (
                <CardContent className="pt-0">
                  <div className="flex gap-1 flex-wrap">
                    {goal.metadata.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Pagination info */}
      {data && data.total > 0 && (
        <p className="text-sm text-muted-foreground text-center mt-6">
          Showing {goals.length} of {data.total} goals
        </p>
      )}
    </div>
  );
}
