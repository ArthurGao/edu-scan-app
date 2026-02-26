import { View, Text, StyleSheet } from 'react-native';
import { Link } from 'expo-router';
import { colors, spacing, typography } from '@/theme';

export default function RegisterScreen() {
  // TODO: Implement registration form
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Create Account</Text>
      <Text style={styles.subtitle}>Join EduScan today</Text>

      {/* TODO: Add registration form */}
      <View style={styles.form}>
        <Text style={styles.placeholder}>Registration form goes here</Text>
      </View>

      <Link href={'/auth/login' as any} style={styles.link}>
        <Text style={styles.linkText}>Already have an account? Sign in</Text>
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: spacing[6],
    backgroundColor: colors.white,
  },
  title: {
    ...typography.h2,
    color: colors.gray[900],
    textAlign: 'center',
    marginBottom: spacing[2],
  },
  subtitle: {
    ...typography.body,
    color: colors.gray[500],
    textAlign: 'center',
    marginBottom: spacing[8],
  },
  form: {
    marginBottom: spacing[6],
  },
  placeholder: {
    ...typography.body,
    color: colors.gray[400],
    textAlign: 'center',
  },
  link: {
    alignSelf: 'center',
  },
  linkText: {
    ...typography.bodySmall,
    color: colors.primary,
  },
});
