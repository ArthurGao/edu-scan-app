import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { Platform } from 'react-native';

const mmkvStorage = Platform.OS === 'web'
  ? {
    getItem: (name: string) => localStorage.getItem(name),
    setItem: (name: string, value: string) => localStorage.setItem(name, value),
    removeItem: (name: string) => localStorage.removeItem(name),
  }
  : (() => {
    const { MMKV } = require('react-native-mmkv');
    const storage = new MMKV();
    return {
      getItem: (name: string) => storage.getString(name) ?? null,
      setItem: (name: string, value: string) => storage.set(name, value),
      removeItem: (name: string) => storage.delete(name),
    };
  })();

interface SettingsState {
  defaultAIProvider: AIProvider;
  gradeLevel: string | null;
  darkMode: boolean;
  notifications: boolean;
}

interface SettingsActions {
  setDefaultAIProvider: (provider: AIProvider) => void;
  setGradeLevel: (level: string | null) => void;
  setDarkMode: (enabled: boolean) => void;
  setNotifications: (enabled: boolean) => void;
}

type SettingsStore = SettingsState & SettingsActions;

// MMKV storage adapter
const store = (set: any) => ({
  // State
  defaultAIProvider: 'claude',
  gradeLevel: null,
  darkMode: false,
  notifications: true,

  // Actions
  setDefaultAIProvider: (provider) => set({ defaultAIProvider: provider }),
  setGradeLevel: (level) => set({ gradeLevel: level }),
  setDarkMode: (enabled) => set({ darkMode: enabled }),
  setNotifications: (enabled) => set({ notifications: enabled }),
});

export const useSettingsStore = create<SettingsStore>()(
  (Platform.OS === 'web'
    ? store
    : persist(store, {
      name: 'settings-storage',
      storage: createJSONStorage(() => mmkvStorage as any),
    })) as any
);
