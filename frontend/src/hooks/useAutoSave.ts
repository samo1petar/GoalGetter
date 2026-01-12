'use client';

import { useRef, useCallback, useState } from 'react';

interface UseAutoSaveOptions {
  delay?: number;
  onSave: (content: string) => Promise<void>;
}

export function useAutoSave({ delay = 2000, onSave }: UseAutoSaveOptions) {
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pendingContentRef = useRef<string | null>(null);

  const save = useCallback(
    async (content: string) => {
      setIsSaving(true);
      try {
        await onSave(content);
        setLastSaved(new Date());
      } catch (error) {
        console.error('Auto-save failed:', error);
      } finally {
        setIsSaving(false);
      }
    },
    [onSave]
  );

  const debouncedSave = useCallback(
    (content: string) => {
      pendingContentRef.current = content;

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        if (pendingContentRef.current !== null) {
          save(pendingContentRef.current);
          pendingContentRef.current = null;
        }
      }, delay);
    },
    [delay, save]
  );

  const saveNow = useCallback(
    (content: string) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      pendingContentRef.current = null;
      save(content);
    },
    [save]
  );

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    pendingContentRef.current = null;
  }, []);

  return {
    debouncedSave,
    saveNow,
    cancel,
    isSaving,
    lastSaved,
  };
}
