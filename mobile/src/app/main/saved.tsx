import { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  StatusBar,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Feather, MaterialIcons } from '@expo/vector-icons';
import { colors, spacing, borderRadius } from '@/theme';

const FILTER_TABS = ['All', 'Saved', 'Mistakes', 'Important'] as const;
type FilterTab = (typeof FILTER_TABS)[number];

interface SavedItem {
  id: string;
  subject: string;
  subjectColor: string;
  subjectBg: string;
  question: string;
  date: string;
  isStarred: boolean;
  isMistake: boolean;
}

const MOCK_ITEMS: SavedItem[] = [
  {
    id: '1',
    subject: 'Calculus',
    subjectColor: colors.primary,
    subjectBg: colors.primaryBg,
    question: '∫x²sin(x)dx = ?',
    date: 'Solved on Dec 15, 2024',
    isStarred: true,
    isMistake: true,
  },
  {
    id: '2',
    subject: 'Physics',
    subjectColor: colors.secondary,
    subjectBg: colors.secondaryBg,
    question: 'Calculate force when m=5kg, a=10m/s²',
    date: 'Solved on Dec 14, 2024',
    isStarred: true,
    isMistake: false,
  },
];

export default function SavedScreen() {
  const insets = useSafeAreaInsets();
  const [activeFilter, setActiveFilter] = useState<FilterTab>('All');

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />

      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <Text style={styles.title}>My Collection</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filterRow}
        >
          {FILTER_TABS.map((tab) => (
            <TouchableOpacity
              key={tab}
              style={[
                styles.filterTab,
                activeFilter === tab && styles.filterTabActive,
              ]}
              onPress={() => setActiveFilter(tab)}
            >
              <Text
                style={[
                  styles.filterTabText,
                  activeFilter === tab && styles.filterTabTextActive,
                ]}
              >
                {tab}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Items List */}
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
      >
        {MOCK_ITEMS.map((item) => (
          <TouchableOpacity key={item.id} style={styles.itemCard}>
            <View style={styles.itemHeader}>
              <View
                style={[styles.subjectTag, { backgroundColor: item.subjectBg }]}
              >
                <Text
                  style={[styles.subjectText, { color: item.subjectColor }]}
                >
                  {item.subject}
                </Text>
              </View>
              <View style={styles.itemIcons}>
                {item.isStarred && (
                  <Feather name="star" size={18} color={colors.warning} />
                )}
                {item.isMistake && (
                  <MaterialIcons name="cancel" size={18} color={colors.error} />
                )}
              </View>
            </View>
            <Text style={styles.itemQuestion}>{item.question}</Text>
            <Text style={styles.itemDate}>{item.date}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.white,
  },
  header: {
    paddingHorizontal: spacing[5],
    paddingBottom: 0,
    gap: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.slate[900],
  },
  filterRow: {
    gap: 12,
    paddingBottom: spacing[4],
  },
  filterTab: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 999,
    backgroundColor: colors.slate[50],
  },
  filterTabActive: {
    backgroundColor: colors.primary,
  },
  filterTabText: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.slate[500],
  },
  filterTabTextActive: {
    color: colors.white,
  },
  scrollView: {
    flex: 1,
  },
  listContent: {
    paddingHorizontal: spacing[5],
    paddingTop: spacing[4],
    paddingBottom: spacing[6],
    gap: 12,
  },
  itemCard: {
    backgroundColor: colors.slate[50],
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    gap: 12,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  subjectTag: {
    paddingVertical: 4,
    paddingHorizontal: 12,
    borderRadius: 999,
  },
  subjectText: {
    fontSize: 12,
    fontWeight: '500',
  },
  itemIcons: {
    flexDirection: 'row',
    gap: 12,
  },
  itemQuestion: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.slate[900],
  },
  itemDate: {
    fontSize: 12,
    color: colors.slate[500],
  },
});
