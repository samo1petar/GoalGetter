'use client';

import { useEffect, useMemo } from 'react';
import { BlockNoteView } from '@blocknote/mantine';
import { useCreateBlockNote } from '@blocknote/react';
import type { PartialBlock } from '@blocknote/core';
import '@blocknote/core/fonts/inter.css';
import '@blocknote/mantine/style.css';
import { useAutoSave } from '@/hooks/useAutoSave';
import { useGoalMutations } from '@/hooks/useGoals';
import { Loader2 } from 'lucide-react';

interface GoalEditorProps {
  goalId: string;
  initialContent?: string;
  onContentChange?: (content: string) => void;
}

export function GoalEditor({ goalId, initialContent, onContentChange }: GoalEditorProps) {
  const { updateGoal } = useGoalMutations();

  // Parse initial content
  const initialBlocks = useMemo(() => {
    if (!initialContent) return undefined;
    try {
      const parsed = JSON.parse(initialContent);
      return Array.isArray(parsed) ? parsed as PartialBlock[] : undefined;
    } catch {
      // If not JSON, create a paragraph block with the content
      return [
        {
          type: 'paragraph' as const,
          content: initialContent,
        },
      ];
    }
  }, [initialContent]);

  const editor = useCreateBlockNote({
    initialContent: initialBlocks,
  });

  const { debouncedSave, isSaving } = useAutoSave({
    delay: 2000,
    onSave: async (content: string) => {
      await updateGoal.mutateAsync({
        goalId,
        data: { content },
      });
    },
  });

  // Handle content changes
  useEffect(() => {
    if (!editor) return;

    const handleChange = () => {
      const content = JSON.stringify(editor.document);
      onContentChange?.(content);
      debouncedSave(content);
    };

    // Subscribe to changes
    const unsubscribe = editor.onChange(handleChange);

    return () => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, [editor, onContentChange, debouncedSave]);

  return (
    <div className="relative h-full">
      {isSaving && (
        <div className="absolute top-2 right-2 flex items-center gap-1 text-xs text-muted-foreground z-10">
          <Loader2 className="h-3 w-3 animate-spin" />
          Saving...
        </div>
      )}
      <BlockNoteView
        editor={editor}
        theme="light"
        className="h-full"
      />
    </div>
  );
}
