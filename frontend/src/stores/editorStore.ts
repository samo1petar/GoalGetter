import { create } from 'zustand';

interface EditorState {
  // Current editor's save function
  saveCurrentGoal: (() => Promise<void>) | null;
  // Track if there are unsaved changes
  hasUnsavedChanges: boolean;
  // Currently editing goal ID
  currentGoalId: string | null;

  // Actions
  registerSaveFunction: (goalId: string, saveFn: () => Promise<void>) => void;
  unregisterSaveFunction: (goalId: string) => void;
  setHasUnsavedChanges: (hasChanges: boolean) => void;
  saveIfNeeded: () => Promise<void>;
}

export const useEditorStore = create<EditorState>((set, get) => ({
  saveCurrentGoal: null,
  hasUnsavedChanges: false,
  currentGoalId: null,

  registerSaveFunction: (goalId, saveFn) => {
    set({
      currentGoalId: goalId,
      saveCurrentGoal: saveFn,
      hasUnsavedChanges: false,
    });
  },

  unregisterSaveFunction: (goalId) => {
    const state = get();
    // Only unregister if it's the same goal
    if (state.currentGoalId === goalId) {
      set({
        currentGoalId: null,
        saveCurrentGoal: null,
        hasUnsavedChanges: false,
      });
    }
  },

  setHasUnsavedChanges: (hasChanges) => {
    set({ hasUnsavedChanges: hasChanges });
  },

  saveIfNeeded: async () => {
    const state = get();
    if (state.hasUnsavedChanges && state.saveCurrentGoal) {
      try {
        await state.saveCurrentGoal();
        set({ hasUnsavedChanges: false });
      } catch (error) {
        console.error('Failed to save goal:', error);
        throw error;
      }
    }
  },
}));
