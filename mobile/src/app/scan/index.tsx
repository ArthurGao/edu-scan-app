import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  StatusBar,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, borderRadius } from '@/theme';

export default function ScanScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const handleCapture = () => {
    // TODO: Integrate with expo-camera to capture image
    // For now, navigate to result screen with mock data
    router.push('/scan/result' as any);
  };

  const handleUpload = () => {
    // TODO: Integrate with expo-image-picker
  };

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
        <Text style={styles.headerTitle}>Scan Question</Text>
        <TouchableOpacity style={styles.headerBtn}>
          <Feather name="zap" size={20} color={colors.slate[900]} />
        </TouchableOpacity>
      </View>

      {/* Camera View */}
      <View style={styles.cameraView}>
        <View style={styles.scanFrame} />
        <Text style={styles.cameraHint}>Position question within frame</Text>
      </View>

      {/* Controls */}
      <View style={styles.controls}>
        <TouchableOpacity onPress={handleCapture} activeOpacity={0.8}>
          <LinearGradient
            colors={[colors.primary, '#8B5CF6']}
            start={{ x: 0, y: 0 }}
            end={{ x: 0, y: 1 }}
            style={styles.captureBtn}
          >
            <Feather name="camera" size={24} color={colors.white} />
            <Text style={styles.captureText}>Capture Question</Text>
          </LinearGradient>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.uploadBtn}
          onPress={handleUpload}
          activeOpacity={0.7}
        >
          <Feather name="image" size={20} color={colors.slate[500]} />
          <Text style={styles.uploadText}>Upload from Gallery</Text>
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
  cameraView: {
    flex: 1,
    backgroundColor: '#1A1A1A',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing[6],
    gap: 16,
  },
  scanFrame: {
    width: 320,
    height: 200,
    borderRadius: borderRadius.lg,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.8)',
    opacity: 0.8,
  },
  cameraHint: {
    fontSize: 14,
    color: colors.white,
    opacity: 0.7,
    textAlign: 'center',
  },
  controls: {
    backgroundColor: colors.white,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: 32,
    gap: 20,
  },
  captureBtn: {
    height: 56,
    borderRadius: 28,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  captureText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.white,
  },
  uploadBtn: {
    height: 48,
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    borderColor: colors.slate[200],
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  uploadText: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.slate[500],
  },
});
