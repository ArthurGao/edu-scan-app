import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/stores';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 1000 * 60 * 5, // 5 minutes
    },
  },
});

export default function RootLayout() {
  const loadUser = useAuthStore((state) => state.loadUser);
  const accessToken = useAuthStore((state) => state.accessToken);

  useEffect(() => {
    if (accessToken) {
      loadUser();
    }
  }, [accessToken]);

  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="auth" />
        <Stack.Screen name="main" />
        <Stack.Screen name="scan" options={{ presentation: 'fullScreenModal' }} />
      </Stack>
    </QueryClientProvider>
  );
}
