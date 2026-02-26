import { create } from 'zustand';
import { ScanResult, ScanState, SolveRequest } from '@/types';
import { scanService } from '@/services';

interface ScanActions {
  solve: (data: SolveRequest) => Promise<ScanResult>;
  clearScan: () => void;
  setError: (error: string | null) => void;
}

type ScanStore = ScanState & ScanActions;

export const useScanStore = create<ScanStore>((set) => ({
  // State
  isScanning: false,
  isProcessing: false,
  currentScan: null,
  error: null,

  // Actions
  solve: async (data: SolveRequest) => {
    set({ isProcessing: true, error: null });
    try {
      const result = await scanService.solve(data);
      set({ currentScan: result, isProcessing: false });
      return result;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to solve problem';
      set({ error: errorMessage, isProcessing: false });
      throw error;
    }
  },

  clearScan: () => {
    set({ currentScan: null, error: null });
  },

  setError: (error: string | null) => {
    set({ error });
  },
}));
