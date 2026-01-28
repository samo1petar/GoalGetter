'use client';

import { useRef, useCallback, useState, useEffect } from 'react';

interface UseAutoSaveOptions {
  /** Delay in ms before auto-saving after last change. Default: 60000 (60 seconds) */
  delay?: number;
  onSave: (content: string) => Promise<void>;
}

/**
 * Hook for managing auto-save with idle-based triggering.
 * Saves after a period of inactivity (default 60 seconds) to avoid
 * disrupting the user's editing flow.
 */
export function useAutoSave({ delay = 60000, onSave }: UseAutoSaveOptions) {
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pendingContentRef = useRef<string | null>(null);
  const isSavingRef = useRef(false);

  const save = useCallback(
    async (content: string) => {
      if (isSavingRef.current) return;

      isSavingRef.current = true;
      setIsSaving(true);
      try {
        await onSave(content);
        setLastSaved(new Date());
        setHasUnsavedChanges(false);
        pendingContentRef.current = null;
      } catch (error) {
        console.error('Auto-save failed:', error);
      } finally {
        isSavingRef.current = false;
        setIsSaving(false);
      }
    },
    [onSave]
  );

  const debouncedSave = useCallback(
    (content: string) => {
      pendingContentRef.current = content;
      setHasUnsavedChanges(true);

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        if (pendingContentRef.current !== null) {
          save(pendingContentRef.current);
        }
      }, delay);
    },
    [delay, save]
  );

  /**
   * Save immediately if there are pending changes.
   * Returns a promise that resolves when save is complete.
   */
  const saveNow = useCallback(async () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (pendingContentRef.current !== null) {
      await save(pendingContentRef.current);
    }
  }, [save]);

  /**
   * Save with specific content immediately.
   */
  const saveNowWithContent = useCallback(
    async (content: string) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      pendingContentRef.current = null;
      await save(content);
    },
    [save]
  );

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    pendingContentRef.current = null;
    setHasUnsavedChanges(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    debouncedSave,
    saveNow,
    saveNowWithContent,
    cancel,
    isSaving,
    lastSaved,
    hasUnsavedChanges,
  };
}
