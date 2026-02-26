export const colors = {
  // Primary
  primary: '#6366F1',
  primaryLight: '#818CF8',
  primaryDark: '#4F46E5',
  primaryBg: '#EEF2FF',
  primaryBgLight: '#E0E7FF',

  // Secondary
  secondary: '#10B981',
  secondaryLight: '#34D399',
  secondaryDark: '#059669',
  secondaryBg: '#D1FAE5',
  secondaryText: '#047857',

  // Neutral
  white: '#FFFFFF',
  black: '#000000',
  slate: {
    50: '#F8FAFC',
    100: '#F1F5F9',
    200: '#E2E8F0',
    300: '#CBD5E1',
    400: '#94A3B8',
    500: '#64748B',
    600: '#475569',
    700: '#334155',
    800: '#1E293B',
    900: '#0F172A',
  },
  gray: {
    50: '#F9FAFB',
    100: '#F3F4F6',
    200: '#E5E7EB',
    300: '#D1D5DB',
    400: '#9CA3AF',
    500: '#6B7280',
    600: '#4B5563',
    700: '#374151',
    800: '#1F2937',
    900: '#111827',
  },

  // Semantic
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#3B82F6',

  // Subject colors
  subjects: {
    math: '#4F46E5',
    physics: '#0EA5E9',
    chemistry: '#8B5CF6',
    biology: '#10B981',
    english: '#F59E0B',
    chinese: '#EF4444',
    history: '#F97316',
    geography: '#14B8A6',
  },
};

export const darkColors = {
  ...colors,
  background: '#111827',
  surface: '#1F2937',
  text: '#F9FAFB',
  textSecondary: '#9CA3AF',
};

export const lightColors = {
  ...colors,
  background: '#F9FAFB',
  surface: '#FFFFFF',
  text: '#111827',
  textSecondary: '#6B7280',
};
