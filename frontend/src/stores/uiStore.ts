import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  panelSizes: number[];
  sidebarOpen: boolean;
  activeGoalId: string | null;

  setPanelSizes: (sizes: number[]) => void;
  setSidebarOpen: (open: boolean) => void;
  setActiveGoalId: (id: string | null) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      panelSizes: [50, 50],
      sidebarOpen: false,
      activeGoalId: null,

      setPanelSizes: (panelSizes) => set({ panelSizes }),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      setActiveGoalId: (activeGoalId) => set({ activeGoalId }),
    }),
    {
      name: 'goalgetter-ui',
      partialize: (state) => ({
        panelSizes: state.panelSizes,
      }),
    }
  )
);
