import { View, Text, StyleSheet } from 'react-native';
import { Link } from 'expo-router';
import { colors, spacing, typography } from '@/theme';

export default function LoginScreen() {
  // TODO: Implement login form
  return (
    <View style={styles.container}>
      <Text style={styles.title}>EduScan</Text>
      <Text style={styles.subtitle}>Sign in to continue</Text>

      {/* TODO: Add login form */}
      <View style={styles.form}>
        <Text style={styles.placeholder}>Login form goes here</Text>
      </View>

      <Link href={'/auth/register' as any} style={styles.link}>
        <Text style={styles.linkText}>Don't have an account? Sign up</Text>
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
    ...typography.h1,
    color: colors.primary,
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
