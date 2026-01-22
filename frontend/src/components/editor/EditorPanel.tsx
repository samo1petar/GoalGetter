'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { GoalEditor } from './GoalEditor';
import { GoalSelector } from './GoalSelector';
import { useGoal, useGoalMutations } from '@/hooks/useGoals';
import { useUIStore } from '@/stores/uiStore';
import { useDraftGoals } from '@/hooks/useDraftGoals';
import { useChatStore } from '@/stores/chatStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Download,
  MoreVertical,
  Trash2,
  CheckCircle,
  Archive,
  PlayCircle,
  FileText,
  Undo2,
  Redo2,
} from 'lucide-react';
import type { BlockNoteEditor } from '@blocknote/core';

export function EditorPanel() {
  const { activeGoalId, setActiveGoalId } = useUIStore();
  const { data: goalFromQuery, isLoading } = useGoal(activeGoalId);
  const { updateGoalPhase, deleteGoal, exportGoal } = useGoalMutations();
  const { setDraft, setActiveEditingGoalId } = useDraftGoals();
  const { aiUpdatedGoal, setAiUpdatedGoal } = useChatStore();
  const [editor, setEditor] = useState<BlockNoteEditor | null>(null);

  // Use AI-updated goal if it matches the active goal, otherwise use query data
  // This provides immediate updates when AI Coach modifies a goal
  const goal = useMemo(() => {
    if (aiUpdatedGoal && activeGoalId && aiUpdatedGoal.id === activeGoalId) {
      return aiUpdatedGoal;
    }
    return goalFromQuery;
  }, [aiUpdatedGoal, activeGoalId, goalFromQuery]);

  // Clear AI-updated goal when switching goals or when query data catches up
  useEffect(() => {
    if (aiUpdatedGoal && goalFromQuery) {
      // If query data has caught up (same updated_at), clear the AI-updated goal
      if (
        aiUpdatedGoal.id === goalFromQuery.id &&
        aiUpdatedGoal.updated_at === goalFromQuery.updated_at
      ) {
        setAiUpdatedGoal(null);
      }
    }
  }, [aiUpdatedGoal, goalFromQuery, setAiUpdatedGoal]);

  // Clear AI-updated goal when switching to a different goal
  useEffect(() => {
    if (aiUpdatedGoal && activeGoalId && aiUpdatedGoal.id !== activeGoalId) {
      setAiUpdatedGoal(null);
    }
  }, [aiUpdatedGoal, activeGoalId, setAiUpdatedGoal]);

  // Handle content changes from the editor - update draft with both JSON and Markdown
  const handleContentChange = useCallback(
    (content: string, markdown: string) => {
      if (goal) {
        setDraft(goal.id, {
          id: goal.id,
          title: goal.title,
          content: content,
          contentMarkdown: markdown,
          template_type: goal.template_type,
        });
        setActiveEditingGoalId(goal.id);
      }
    },
    [goal, setDraft, setActiveEditingGoalId]
  );

  const handleExport = () => {
    if (goal) {
      exportGoal(goal.id, goal.title);
    }
  };

  const handlePhaseChange = (phase: string) => {
    if (goal) {
      updateGoalPhase.mutate({ goalId: goal.id, phase });
    }
  };

  const handleDelete = () => {
    if (goal && confirm('Are you sure you want to delete this goal?')) {
      deleteGoal.mutate(goal.id);
      setActiveGoalId(null);
    }
  };

  const phaseColors: Record<string, string> = {
    draft: 'bg-yellow-100 text-yellow-800',
    active: 'bg-green-100 text-green-800',
    completed: 'bg-blue-100 text-blue-800',
    archived: 'bg-gray-100 text-gray-800',
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b">
        <div className="flex items-center gap-3">
          <GoalSelector
            value={activeGoalId}
            onChange={setActiveGoalId}
          />
          {goal && (
            <Badge className={phaseColors[goal.phase] || ''} variant="secondary">
              {goal.phase}
            </Badge>
          )}
          {editor && (
            <div className="flex items-center gap-1 ml-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => editor.undo()}
                title="Undo (Ctrl+Z)"
              >
                <Undo2 className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => editor.redo()}
                title="Redo (Ctrl+Y)"
              >
                <Redo2 className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        {goal && (
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleExport}>
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handlePhaseChange('active')}>
                  <PlayCircle className="mr-2 h-4 w-4" />
                  Set Active
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handlePhaseChange('completed')}>
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Mark Complete
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handlePhaseChange('archived')}>
                  <Archive className="mr-2 h-4 w-4" />
                  Archive
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={handleDelete}
                  className="text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>

      {/* Editor Content */}
      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        ) : goal ? (
          <div className="h-full">
            <div className="px-4 py-3 border-b">
              <h1 className="text-xl font-semibold">{goal.title}</h1>
              {goal.metadata.deadline && (
                <p className="text-sm text-muted-foreground mt-1">
                  Deadline: {new Date(goal.metadata.deadline).toLocaleDateString()}
                </p>
              )}
            </div>
            <div className="p-4">
              <GoalEditor
                key={goal.id}
                goalId={goal.id}
                initialContent={goal.content}
                contentFormat={goal.metadata.content_format}
                onContentChange={handleContentChange}
                onEditorReady={setEditor}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No goal selected</h3>
            <p className="text-muted-foreground mb-4">
              Select a goal from the dropdown or create a new one to get started.
            </p>
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
