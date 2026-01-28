'use client';

import { useEffect, useMemo, useCallback, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import { BlockNoteView } from '@blocknote/mantine';
import { useCreateBlockNote } from '@blocknote/react';
import type { PartialBlock, Block, BlockNoteEditor } from '@blocknote/core';
import { closeHistory } from 'prosemirror-history';
import '@blocknote/core/fonts/inter.css';
import '@blocknote/mantine/style.css';
import { useAutoSave } from '@/hooks/useAutoSave';
import { useGoalMutations } from '@/hooks/useGoals';
import { useEditorStore } from '@/stores/editorStore';
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
  onEditorReady?: (editor: BlockNoteEditor) => void;
}

export function GoalEditor({ goalId, initialContent, contentFormat, onContentChange, onEditorReady }: GoalEditorProps) {
  const { updateGoal } = useGoalMutations();
  const { resolvedTheme } = useTheme();
  const { registerSaveFunction, unregisterSaveFunction, setHasUnsavedChanges } = useEditorStore();
  const [mounted, setMounted] = useState(false);
  const isUpdatingFromExternal = useRef(false);
  // Track the last content we processed to detect external changes
  const lastProcessedContent = useRef<string | undefined>(undefined);
  // Track the last content we saved to prevent refresh loop
  const lastSavedContent = useRef<string | undefined>(undefined);
  // Track if this is the initial mount
  const isInitialMount = useRef(true);
  // Store current content for save function
  const currentContentRef = useRef<string | null>(null);

  // Handle hydration for theme
  useEffect(() => {
    setMounted(true);
  }, []);

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

  // Helper to clear undo history - prevents undoing past initial content
  const clearUndoHistory = useCallback(() => {
    if (!editor) return;
    try {
      // Access the underlying ProseMirror view via Tiptap
      const tiptapEditor = (editor as unknown as { _tiptapEditor: { view: { state: { tr: unknown }, dispatch: (tr: unknown) => void } } })._tiptapEditor;
      if (tiptapEditor?.view) {
        const { state, dispatch } = tiptapEditor.view;
        dispatch(closeHistory(state.tr as Parameters<typeof closeHistory>[0]));
      }
    } catch (error) {
      console.warn('Failed to clear undo history:', error);
    }
  }, [editor]);

  // Expose editor instance to parent component
  useEffect(() => {
    if (editor && onEditorReady) {
      onEditorReady(editor);
    }
  }, [editor, onEditorReady]);

  // Convert Markdown initial content after editor is ready (only on mount)
  // Then clear undo history to prevent undoing past initial content
  useEffect(() => {
    if (!editor || !initialContent) return;
    // Only run this on initial mount - subsequent updates are handled by the
    // external content change detection effect below
    if (!isInitialMount.current) return;

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

    // Clear undo history after initial content is loaded
    // This prevents users from undoing past the initial goal content
    // Use setTimeout to ensure the content replacement transaction is complete
    setTimeout(() => {
      clearUndoHistory();
    }, 0);
  }, [editor, initialContent, isMarkdownContent, clearUndoHistory]);

  const { debouncedSave, saveNow, isSaving, hasUnsavedChanges } = useAutoSave({
    delay: 60000, // 60 seconds idle before auto-save
    onSave: async (content: string) => {
      lastSavedContent.current = content;
      await updateGoal.mutateAsync({
        goalId,
        data: { content },
      });
    },
  });

  // Sync hasUnsavedChanges with editorStore (use ref to prevent loops)
  const prevHasUnsavedChanges = useRef(hasUnsavedChanges);
  useEffect(() => {
    if (prevHasUnsavedChanges.current !== hasUnsavedChanges) {
      prevHasUnsavedChanges.current = hasUnsavedChanges;
      setHasUnsavedChanges(hasUnsavedChanges);
    }
  }, [hasUnsavedChanges, setHasUnsavedChanges]);

  // Store updateGoal ref to avoid dependency issues
  const updateGoalRef = useRef(updateGoal);
  updateGoalRef.current = updateGoal;

  // Register save function with global store for external triggers
  useEffect(() => {
    const saveFunction = async () => {
      if (currentContentRef.current) {
        lastSavedContent.current = currentContentRef.current;
        await updateGoalRef.current.mutateAsync({
          goalId,
          data: { content: currentContentRef.current },
        });
      }
    };

    registerSaveFunction(goalId, saveFunction);

    return () => {
      unregisterSaveFunction(goalId);
    };
  }, [goalId, registerSaveFunction, unregisterSaveFunction]);

  // Save before page unload
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        // Trigger save (best effort, may not complete)
        saveNow();
        // Show browser's default "unsaved changes" dialog
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [hasUnsavedChanges, saveNow]);

  // Handle content changes with Markdown conversion
  const handleEditorChange = useCallback(() => {
    if (!editor || isUpdatingFromExternal.current) return;

    const content = JSON.stringify(editor.document);
    currentContentRef.current = content;

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

  // Detect external content changes (e.g., from AI Coach updates)
  // This effect runs when initialContent prop changes after the initial mount
  useEffect(() => {
    // Skip the initial mount - content is already set via initialBlocks or the Markdown conversion effect
    if (isInitialMount.current) {
      isInitialMount.current = false;
      lastProcessedContent.current = initialContent;
      return;
    }

    // If content hasn't changed from what we last processed, skip
    if (initialContent === lastProcessedContent.current) {
      return;
    }

    // If this content matches what we just saved, skip (prevents refresh loop)
    if (initialContent === lastSavedContent.current) {
      lastProcessedContent.current = initialContent;
      return;
    }

    // Content has changed externally (e.g., AI Coach updated the goal)
    // Update the editor with the new content
    if (initialContent !== undefined && editor) {
      console.log('[GoalEditor] External content change detected, updating editor', {
        hasContentFormat: !!contentFormat,
        contentLength: initialContent.length,
        previousLength: lastProcessedContent.current?.length ?? 0,
      });
      updateContent(initialContent, contentFormat);
      lastProcessedContent.current = initialContent;
      // Also update current content ref so save won't overwrite with old content
      currentContentRef.current = initialContent;
    }
  }, [initialContent, contentFormat, updateContent, editor]);

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
        theme={mounted && resolvedTheme === 'dark' ? 'dark' : 'light'}
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
