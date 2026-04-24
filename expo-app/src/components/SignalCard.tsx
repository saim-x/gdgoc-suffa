import { Pressable, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import type { SignalInsight } from "../types";
import { colors, radius, spacing } from "../theme";

type SignalCardProps = {
  signal: SignalInsight;
  onPress?: () => void;
};

export function SignalCard({ signal, onPress }: SignalCardProps) {
  const confidence = Math.max(0, Math.min(100, signal.confidence));
  const actionColor =
    signal.action === "buy" ? colors.profit : signal.action === "sell" ? colors.loss : colors.warning;

  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.shell, pressed && styles.pressed]}>
      <View style={styles.card}>
        <View style={styles.topRow}>
          <Text style={styles.asset}>{signal.asset}</Text>
          <Text style={[styles.action, { color: actionColor }]}>{signal.action.toUpperCase()}</Text>
        </View>
        <View style={styles.barTrack}>
          <LinearGradient
            colors={["#9BE7BF", "#5CCF9D", "#20A86F"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={[styles.barFill, { width: `${confidence}%` }]}
          />
        </View>
        <View style={styles.bottomRow}>
          <Text style={styles.confidence}>{confidence}% confidence</Text>
          <Text style={styles.time}>
            {new Date(signal.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  shell: {
    width: 188,
    borderRadius: radius.lg,
    marginRight: spacing.md,
    borderWidth: 1,
    borderColor: "rgba(204, 220, 206, 0.4)",
    backgroundColor: "#FFFFFF",
    padding: 1.5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.04,
    shadowRadius: 10,
    elevation: 2,
    marginBottom: 8,
  },
  card: {
    borderRadius: radius.lg - 2,
    backgroundColor: colors.panelRaised,
    padding: spacing.md,
    gap: spacing.md,
  },
  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  asset: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 16,
  },
  action: {
    fontFamily: "Inter_700Bold",
    fontSize: 11,
    letterSpacing: 0.6,
  },
  barTrack: {
    width: "100%",
    height: 7,
    borderRadius: radius.pill,
    backgroundColor: "#E5EFE8",
    overflow: "hidden",
  },
  barFill: {
    height: 7,
    borderRadius: radius.pill,
  },
  bottomRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  confidence: {
    color: colors.textSoft,
    fontFamily: "Inter_500Medium",
    fontSize: 12,
  },
  time: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 11,
  },
  pressed: {
    transform: [{ scale: 0.985 }],
  },
});
