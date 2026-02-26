import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  StatusBar,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, borderRadius } from '@/theme';

export default function ResultScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />

      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <TouchableOpacity
          style={styles.headerBtn}
          onPress={() => router.back()}
        >
          <Feather name="arrow-left" size={20} color={colors.slate[900]} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>AI Solution</Text>
        <TouchableOpacity style={styles.headerBtn}>
          <Feather name="bookmark" size={20} color={colors.slate[500]} />
        </TouchableOpacity>
      </View>

      {/* Content */}
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Question Card */}
        <View style={styles.questionCard}>
          <Text style={styles.cardLabel}>Your Question</Text>
          <View style={styles.questionImage}>
            <Image
              source={{
                uri: 'https://images.unsplash.com/photo-1758685734643-db77920292bc?w=400',
              }}
              style={styles.questionImageInner}
              resizeMode="cover"
            />
          </View>
          <Text style={styles.questionText}>
            Find the integral of x²sin(x)dx
          </Text>
        </View>

        {/* Solution Card */}
        <View style={styles.solutionCard}>
          <Text style={styles.solutionLabel}>Solution</Text>
          <Text style={styles.solutionBody}>
            To solve ∫x²sin(x)dx, we'll use integration by parts twice.
          </Text>
          <Text style={styles.solutionStep}>
            {'Let u = x², dv = sin(x)dx\nThen du = 2x dx, v = -cos(x)'}
          </Text>
          <Text style={styles.solutionFormula}>
            ∫x²sin(x)dx = -x²cos(x) + 2∫xcos(x)dx
          </Text>
        </View>

        {/* Key Concept Card */}
        <View style={styles.conceptCard}>
          <Feather name="sun" size={20} color={colors.secondary} />
          <Text style={styles.conceptTitle}>Key Concept</Text>
          <Text style={styles.conceptText}>
            Integration by parts is useful when integrating products of
            polynomials and trigonometric functions.
          </Text>
        </View>
      </ScrollView>

      {/* Action Bar */}
      <View style={[styles.actionBar, { paddingBottom: insets.bottom + 16 }]}>
        <TouchableOpacity style={styles.followUpBtn}>
          <Feather name="message-circle" size={20} color={colors.primary} />
          <Text style={styles.followUpText}>Ask Follow-up</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.shareBtn}>
          <Feather name="share-2" size={20} color={colors.slate[500]} />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.white,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[5],
    paddingBottom: 12,
  },
  headerBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.slate[50],
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.slate[900],
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: spacing[5],
    gap: 20,
    paddingBottom: spacing[4],
  },
  // Question Card
  questionCard: {
    backgroundColor: colors.slate[50],
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    gap: 12,
  },
  cardLabel: {
    fontSize: 12,
    fontWeight: '500',
    color: colors.slate[500],
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  questionImage: {
    height: 120,
    borderRadius: borderRadius.md,
    overflow: 'hidden',
    backgroundColor: colors.slate[200],
  },
  questionImageInner: {
    width: '100%',
    height: '100%',
  },
  questionText: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.slate[900],
  },
  // Solution Card
  solutionCard: {
    borderRadius: borderRadius.lg,
    padding: spacing[5],
    gap: 16,
    backgroundColor: '#F0F4FF',
  },
  solutionLabel: {
    fontSize: 12,
    fontWeight: '500',
    color: colors.primary,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  solutionBody: {
    fontSize: 15,
    color: colors.slate[900],
    lineHeight: 24,
  },
  solutionStep: {
    fontSize: 14,
    color: colors.slate[500],
    lineHeight: 21,
  },
  solutionFormula: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.slate[900],
    lineHeight: 21,
  },
  // Key Concept Card
  conceptCard: {
    backgroundColor: colors.secondaryBg,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    gap: 12,
  },
  conceptTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.secondary,
  },
  conceptText: {
    fontSize: 13,
    color: colors.secondaryText,
    lineHeight: 19.5,
  },
  // Action Bar
  actionBar: {
    flexDirection: 'row',
    paddingHorizontal: spacing[5],
    paddingTop: spacing[4],
    gap: 12,
    backgroundColor: colors.white,
  },
  followUpBtn: {
    flex: 1,
    height: 48,
    borderRadius: borderRadius.lg,
    borderWidth: 1.5,
    borderColor: colors.primary,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  followUpText: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.primary,
  },
  shareBtn: {
    width: 48,
    height: 48,
    borderRadius: borderRadius.lg,
    backgroundColor: colors.slate[50],
    justifyContent: 'center',
    alignItems: 'center',
  },
});
