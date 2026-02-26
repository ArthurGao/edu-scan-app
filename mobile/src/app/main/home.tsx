import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  StatusBar,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Feather, MaterialIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, typography, borderRadius } from '@/theme';

export default function HomeScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header Gradient */}
        <LinearGradient
          colors={[colors.primary, '#8B5CF6']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.header, { paddingTop: insets.top + 20 }]}
        >
          <Text style={styles.greeting}>Hello, Student!</Text>
          <Text style={styles.subtitle}>
            Ready to learn something new today?
          </Text>
          <View style={styles.statsRow}>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>156</Text>
              <Text style={styles.statLabel}>Questions Solved</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={[styles.statNumber, { color: colors.warning }]}>
                7 Days
              </Text>
              <Text style={styles.statLabel}>Study Streak</Text>
            </View>
          </View>
        </LinearGradient>

        {/* Scan Button */}
        <View style={styles.scanSection}>
          <TouchableOpacity
            style={styles.scanButton}
            onPress={() => router.push('/scan' as any)}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={[colors.primary, '#8B5CF6']}
              style={styles.scanButtonGradient}
            >
              <Feather name="camera" size={48} color={colors.white} />
              <Text style={styles.scanText}>SCAN</Text>
            </LinearGradient>
          </TouchableOpacity>
          <Text style={styles.scanHint}>Tap to scan a question</Text>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.actionsGrid}>
            <TouchableOpacity style={styles.actionCard}>
              <MaterialIcons
                name="history"
                size={24}
                color={colors.primary}
              />
              <Text style={styles.actionText}>History</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.actionCard}
              onPress={() => router.push('/main/saved' as any)}
            >
              <Feather name="bookmark" size={24} color={colors.secondary} />
              <Text style={styles.actionText}>Saved</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionCard}>
              <MaterialIcons name="cancel" size={24} color={colors.error} />
              <Text style={styles.actionText}>Mistakes</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Recent Questions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Questions</Text>
          <View style={styles.recentList}>
            <TouchableOpacity style={styles.recentItem}>
              <View style={styles.recentIcon}>
                <Text style={styles.mathSymbol}>∫</Text>
              </View>
              <View style={styles.recentContent}>
                <Text style={styles.recentTitle}>
                  Calculus: Integration
                </Text>
                <Text style={styles.recentTime}>2 hours ago</Text>
              </View>
              <Feather
                name="chevron-right"
                size={20}
                color={colors.slate[400]}
              />
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.white,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: spacing[6],
  },
  header: {
    paddingHorizontal: spacing[6],
    paddingBottom: 32,
    gap: 20,
  },
  greeting: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.white,
  },
  subtitle: {
    fontSize: 16,
    color: colors.primaryBgLight,
    opacity: 0.9,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    gap: 4,
    opacity: 0.95,
  },
  statNumber: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.primary,
  },
  statLabel: {
    fontSize: 12,
    color: colors.slate[500],
  },
  scanSection: {
    alignItems: 'center',
    paddingVertical: 32,
    gap: 16,
  },
  scanButton: {
    width: 160,
    height: 160,
    borderRadius: 80,
    overflow: 'hidden',
  },
  scanButtonGradient: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  scanText: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.white,
    letterSpacing: 1,
  },
  scanHint: {
    fontSize: 14,
    color: colors.slate[500],
    textAlign: 'center',
  },
  section: {
    paddingHorizontal: spacing[6],
    gap: 16,
    marginBottom: spacing[6],
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.slate[900],
  },
  actionsGrid: {
    flexDirection: 'row',
    gap: 12,
  },
  actionCard: {
    flex: 1,
    backgroundColor: colors.slate[50],
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    alignItems: 'center',
    gap: 8,
  },
  actionText: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.slate[900],
  },
  recentList: {
    gap: 12,
  },
  recentItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.slate[50],
    borderRadius: borderRadius.md,
    padding: spacing[3],
    gap: 12,
  },
  recentIcon: {
    width: 40,
    height: 40,
    borderRadius: borderRadius.base,
    backgroundColor: colors.primaryBg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  mathSymbol: {
    fontSize: 20,
    fontWeight: '600',
    color: colors.primary,
  },
  recentContent: {
    flex: 1,
    gap: 2,
  },
  recentTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.slate[900],
  },
  recentTime: {
    fontSize: 12,
    color: colors.slate[500],
  },
});
