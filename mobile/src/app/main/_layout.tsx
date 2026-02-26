import { Tabs, useRouter } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { colors } from '@/theme';

export default function MainLayout() {
  const router = useRouter();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.slate[500],
        headerShown: false,
        tabBarStyle: {
          height: 84,
          paddingTop: 12,
          paddingBottom: 24,
          borderTopWidth: 1,
          borderTopColor: colors.slate[200],
        },
        tabBarLabelStyle: {
          fontSize: 11,
          marginTop: 4,
        },
      }}
    >
      <Tabs.Screen
        name="home"
        options={{
          title: 'Home',
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="home" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="scan"
        options={{
          title: 'Scan',
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="qr-code-scanner" size={size} color={color} />
          ),
        }}
        listeners={{
          tabPress: (e) => {
            e.preventDefault();
            router.push('/scan' as any);
          },
        }}
      />
      <Tabs.Screen
        name="saved"
        options={{
          title: 'Saved',
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="bookmark" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="person" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
