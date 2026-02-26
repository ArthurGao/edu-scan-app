import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, typography } from '@/theme';

export default function ProfileScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Profile</Text>
      <Text style={styles.subtitle}>Coming soon</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.white,
  },
  title: {
    ...typography.h3,
    color: colors.slate[900],
    marginBottom: spacing[2],
  },
  subtitle: {
    ...typography.body,
    color: colors.slate[500],
  },
});
