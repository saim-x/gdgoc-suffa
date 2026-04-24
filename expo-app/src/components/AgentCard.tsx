import { Pressable, StyleSheet, Switch, Text, View } from "react-native";
import Slider from "@react-native-community/slider";
import type { AgentConfig } from "../types";
import { colors, radius, spacing } from "../theme";
import { GlassCard } from "./GlassCard";

type AgentCardProps = {
  agent: AgentConfig;
  onToggle: (enabled: boolean) => void;
  onCapitalChange: (capital: number) => void;
  onThresholdChange: (value: number) => void;
};

export function AgentCard({ agent, onToggle, onCapitalChange, onThresholdChange }: AgentCardProps) {
  const performanceColor = agent.performance >= 0 ? colors.profit : colors.loss;

  return (
    <GlassCard style={styles.shell} innerStyle={styles.card}>
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <Text style={styles.name}>{agent.name}</Text>
          <Text style={styles.strategy}>{agent.strategy}</Text>
        </View>
        <Switch
          value={agent.status === "active"}
          onValueChange={onToggle}
          trackColor={{ false: "#D5CEBF", true: "#F59E0B" }}
          thumbColor="#FFFFFF"
        />
      </View>

      <View style={styles.statsRow}>
        <Text style={styles.statLabel}>Assigned: {agent.assignedCapital.toLocaleString()}</Text>
        <Text style={[styles.statLabel, { color: performanceColor }]}>
          {agent.performance >= 0 ? "+" : ""}
          {agent.performance.toFixed(1)}%
        </Text>
      </View>

      <View style={styles.sliderBlock}>
        <Text style={styles.sliderLabel}>Capital Allocation</Text>
        <Slider
          value={agent.assignedCapital}
          onValueChange={onCapitalChange}
          minimumValue={10000}
          maximumValue={120000}
          step={1000}
          minimumTrackTintColor={colors.aiBlue}
          maximumTrackTintColor="#E7E1D4"
          thumbTintColor="#D97706"
        />
      </View>

      <View style={styles.sliderBlock}>
        <Text style={styles.sliderLabel}>Confidence Threshold: {agent.confidenceThreshold}%</Text>
        <Slider
          value={agent.confidenceThreshold}
          onValueChange={onThresholdChange}
          minimumValue={60}
          maximumValue={95}
          step={1}
          minimumTrackTintColor={colors.aiPurple}
          maximumTrackTintColor="#E7E1D4"
          thumbTintColor="#F59E0B"
        />
      </View>

      <Pressable style={({ pressed }) => [styles.quickButton, pressed && styles.pressed]}>
        <Text style={styles.quickButtonText}>Open Strategy Details</Text>
      </Pressable>
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  shell: {
    marginBottom: spacing.md,
  },
  card: {
    borderRadius: radius.lg,
    padding: spacing.lg,
    gap: spacing.md,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  name: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 17,
  },
  strategy: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 12,
    marginTop: 3,
  },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  statLabel: {
    color: colors.textSoft,
    fontFamily: "Inter_600SemiBold",
    fontSize: 13,
  },
  sliderBlock: {
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FCFBF8",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  sliderLabel: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 12,
    marginBottom: 2,
  },
  quickButton: {
    alignSelf: "flex-start",
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: "#FEF7ED",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  quickButtonText: {
    color: colors.textSoft,
    fontFamily: "Inter_600SemiBold",
    fontSize: 12,
  },
  pressed: {
    transform: [{ scale: 0.98 }],
  },
});
