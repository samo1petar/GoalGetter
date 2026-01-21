'use client';

import { useEffect, useMemo, useCallback, useRef } from 'react';
import { BlockNoteView } from '@blocknote/mantine';
import { useCreateBlockNote } from '@blocknote/react';
import type { PartialBlock, Block } from '@blocknote/core';
import '@blocknote/core/fonts/inter.css';
import '@blocknote/mantine/style.css';
import { useAutoSave } from '@/hooks/useAutoSave';
import { useGoalMutations } from '@/hooks/useGoals';
import { Loader2 } from 'lucide-react';
import {
  blocksToMarkdown,
  markdownToBlocks,
  looksLikeMarkdown,
  isBlockNoteJson,
} from '@/utils/blockNoteMarkdown';
import type { ContentFormat } from '@/types';

interface GoalEditorProps {
  goalId: string;
  initialContent?: string;
  /** Content format hint from goal metadata (set when AI creates/updates content) */
  contentFormat?: ContentFormat;
  onContentChange?: (content: string, markdown: string) => void;
}

export function GoalEditor({ goalId, initialContent, contentFormat, onContentChange }: GoalEditorProps) {
  const { updateGoal } = useGoalMutations();
  const isUpdatingFromExternal = useRef(false);

  // Determine if content is Markdown based on format hint or content analysis
  const isMarkdownContent = useMemo(() => {
    if (contentFormat === 'markdown') return true;
    if (contentFormat === 'blocknote_json') return false;
    // Auto-detect if no format hint
    return initialContent ? looksLikeMarkdown(initialContent) && !isBlockNoteJson(initialContent) : false;
  }, [initialContent, contentFormat]);

  // Parse initial content - handles both BlockNote JSON and Markdown
  const initialBlocks = useMemo(() => {
    if (!initialContent) return undefined;

    // First try to parse as BlockNote JSON (unless we know it's Markdown)
    if (!isMarkdownContent && isBlockNoteJson(initialContent)) {
      try {
        const parsed = JSON.parse(initialContent);
        return Array.isArray(parsed) ? parsed as PartialBlock[] : undefined;
      } catch {
        // Fall through to other handling
      }
    }

    // If content is Markdown, we'll handle conversion after editor init
    if (isMarkdownContent) {
      // Return undefined, we'll convert Markdown after editor is ready
      return undefined;
    }

    // Plain text - create a paragraph block
    return [
      {
        type: 'paragraph' as const,
        content: initialContent,
      },
    ];
  }, [initialContent, isMarkdownContent]);

  const editor = useCreateBlockNote({
    initialContent: initialBlocks,
  });

  // Convert Markdown initial content after editor is ready
  useEffect(() => {
    if (!editor || !initialContent) return;

    // Only convert if content is Markdown (based on format hint or auto-detection)
    if (isMarkdownContent) {
      isUpdatingFromExternal.current = true;
      try {
        const blocks = markdownToBlocks(initialContent, editor);
        if (blocks.length > 0) {
          editor.replaceBlocks(editor.document, blocks);
        }
      } catch (error) {
        console.error('Failed to convert initial Markdown:', error);
      } finally {
        isUpdatingFromExternal.current = false;
      }
    }
  }, [editor, initialContent, isMarkdownContent]);

  const { debouncedSave, isSaving } = useAutoSave({
    delay: 2000,
    onSave: async (content: string) => {
      await updateGoal.mutateAsync({
        goalId,
        data: { content },
      });
    },
  });

  // Handle content changes with Markdown conversion
  const handleEditorChange = useCallback(() => {
    if (!editor || isUpdatingFromExternal.current) return;

    const content = JSON.stringify(editor.document);

    // Convert blocks to Markdown for AI Coach context
    let markdown = '';
    try {
      markdown = blocksToMarkdown(editor.document as PartialBlock[], editor);
    } catch (error) {
      console.error('Failed to convert blocks to Markdown:', error);
      // Markdown will be empty string, which is fine as fallback
    }

    onContentChange?.(content, markdown);
    debouncedSave(content);
  }, [editor, onContentChange, debouncedSave]);

  // Subscribe to content changes
  useEffect(() => {
    if (!editor) return;

    const unsubscribe = editor.onChange(handleEditorChange);

    return () => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, [editor, handleEditorChange]);

  /**
   * Update editor content from external source (e.g., AI Coach).
   * Handles both Markdown and BlockNote JSON formats.
   *
   * @param content - The content string (Markdown or BlockNote JSON)
   * @param format - Optional format hint ('markdown' or 'blocknote_json')
   */
  const updateContent = useCallback(
    (content: string, format?: 'markdown' | 'blocknote_json') => {
      if (!editor || !content) return;

      isUpdatingFromExternal.current = true;

      try {
        let blocks: Block[] | PartialBlock[];

        // Determine format
        const isJson = format === 'blocknote_json' || isBlockNoteJson(content);
        const isMarkdown = format === 'markdown' || (!isJson && looksLikeMarkdown(content));

        if (isJson) {
          // Parse as BlockNote JSON
          blocks = JSON.parse(content) as PartialBlock[];
        } else if (isMarkdown) {
          // Convert Markdown to blocks
          blocks = markdownToBlocks(content, editor);
        } else {
          // Plain text - create a paragraph
          blocks = [
            {
              type: 'paragraph' as const,
              content: content,
            },
          ];
        }

        if (blocks.length > 0) {
          editor.replaceBlocks(editor.document, blocks);
        }
      } catch (error) {
        console.error('Failed to update editor content:', error);
      } finally {
        isUpdatingFromExternal.current = false;
      }
    },
    [editor]
  );

  // Expose updateContent method for parent components via ref or callback
  // For now, we'll handle this through the goal query invalidation flow

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

/**
 * Export the editor with update capability for use with AI Coach.
 * This version provides a ref-based API to update content externally.
 */
export type GoalEditorHandle = {
  updateContent: (content: string, format?: 'markdown' | 'blocknote_json') => void;
};
