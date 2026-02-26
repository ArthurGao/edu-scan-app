import { Redirect } from 'expo-router';
import { useAuthStore } from '@/stores';

export default function Index() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (isAuthenticated) {
    return <Redirect href="/main/home" />;
  }

  return <Redirect href="/auth/login" />;
}
