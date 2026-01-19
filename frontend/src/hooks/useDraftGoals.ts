'use client';

import { create } from 'zustand';

/**
 * Draft goal interface - represents unsaved goal content in the editor
 */
export interface DraftGoal {
  id?: string;           // undefined if new goal, set if editing existing
  title: string;
  content: string;       // Plain text content extracted from editor
  template_type: 'smart' | 'okr' | 'custom';
}

/**
 * Payload format sent to backend with chat messages
 */
export interface DraftGoalPayload {
  id?: string;
  title: string;
  content: string;
  template_type: string;
}

interface DraftGoalsState {
  // Map of goal ID (or 'new' for unsaved) to draft content
  drafts: Map<string, DraftGoal>;
  // Currently active goal being edited
  activeEditingGoalId: string | null;

  // Actions
  setDraft: (goalId: string, draft: DraftGoal) => void;
  removeDraft: (goalId: string) => void;
  clearAllDrafts: () => void;
  setActiveEditingGoalId: (goalId: string | null) => void;
  getDraftsArray: () => DraftGoalPayload[];
}

/**
 * Store for tracking draft (unsaved) goal content.
 * Used to share current editor state with the AI Coach.
 */
export const useDraftGoalsStore = create<DraftGoalsState>((set, get) => ({
  drafts: new Map(),
  activeEditingGoalId: null,

  setDraft: (goalId, draft) =>
    set((state) => {
      const newDrafts = new Map(state.drafts);
      newDrafts.set(goalId, draft);
      return { drafts: newDrafts };
    }),

  removeDraft: (goalId) =>
    set((state) => {
      const newDrafts = new Map(state.drafts);
      newDrafts.delete(goalId);
      return { drafts: newDrafts };
    }),

  clearAllDrafts: () =>
    set({ drafts: new Map() }),

  setActiveEditingGoalId: (goalId) =>
    set({ activeEditingGoalId: goalId }),

  getDraftsArray: () => {
    const { drafts } = get();
    return Array.from(drafts.values()).map((draft) => ({
      id: draft.id,
      title: draft.title,
      content: draft.content,
      template_type: draft.template_type,
    }));
  },
}));

/**
 * Hook to use draft goals functionality
 */
export function useDraftGoals() {
  const {
    drafts,
    activeEditingGoalId,
    setDraft,
    removeDraft,
    clearAllDrafts,
    setActiveEditingGoalId,
    getDraftsArray,
  } = useDraftGoalsStore();

  return {
    drafts,
    activeEditingGoalId,
    setDraft,
    removeDraft,
    clearAllDrafts,
    setActiveEditingGoalId,
    getDraftsArray,
    hasDrafts: drafts.size > 0,
  };
}

/**
 * Utility to parse BlockNote JSON content to plain text
 */
export function parseBlockNoteContent(blocks: unknown[]): string {
  if (!Array.isArray(blocks)) return '';

  const extractText = (content: unknown): string => {
    if (!content) return '';
    if (typeof content === 'string') return content;
    if (Array.isArray(content)) {
      return content.map(extractText).join('');
    }
    if (typeof content === 'object' && content !== null) {
      const obj = content as Record<string, unknown>;
      if (obj.text && typeof obj.text === 'string') {
        return obj.text;
      }
      if (obj.content) {
        return extractText(obj.content);
      }
    }
    return '';
  };

  return blocks
    .map((block) => {
      if (typeof block === 'object' && block !== null) {
        const b = block as Record<string, unknown>;
        const text = extractText(b.content);
        // Add newlines for block-level elements
        if (b.type === 'heading') return `\n${text}\n`;
        if (b.type === 'bulletListItem') return `- ${text}`;
        if (b.type === 'numberedListItem') return `* ${text}`;
        return text;
      }
      return '';
    })
    .filter(Boolean)
    .join('\n');
}
