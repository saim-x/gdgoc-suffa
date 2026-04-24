import { StyleSheet, Text, View } from "react-native";
import { colorForPnl, colors, radius, spacing } from "../theme";
import { GlassCard } from "./GlassCard";

type MetricBoxProps = {
  label: string;
  value: string;
  delta?: string;
  deltaValue?: number;
};

export function MetricBox({ label, value, delta, deltaValue = 0 }: MetricBoxProps) {
  return (
    <GlassCard style={styles.wrap} innerStyle={styles.inner}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
      {delta ? <Text style={[styles.delta, { color: colorForPnl(deltaValue) }]}>{delta}</Text> : null}
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    minWidth: 148,
  },
  inner: {
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.lg,
    gap: spacing.sm,
  },
  label: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 12,
  },
  value: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 22,
    letterSpacing: -0.4,
  },
  delta: {
    fontFamily: "Inter_600SemiBold",
    fontSize: 12,
  },
});
