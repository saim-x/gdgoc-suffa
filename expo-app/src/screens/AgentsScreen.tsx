import { ScrollView, StyleSheet, Text } from "react-native";
import { useMemo } from "react";
import { useTrading } from "../context/TradingContext";
import { colors, radius, spacing } from "../theme";
import { AgentCard } from "../components/AgentCard";

export function AgentsScreen() {
  const { agents, updateAgent } = useTrading();
  const stats = useMemo(() => {
    const active = agents.filter((agent) => agent.status === "active").length;
    const paused = agents.length - active;
    const avgThreshold = agents.length
      ? Math.round(agents.reduce((sum, agent) => sum + agent.confidenceThreshold, 0) / agents.length)
      : 0;
    return { active, paused, avgThreshold };
  }, [agents]);

  return (
    <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <Text style={styles.title}>Agents</Text>
      <Text style={styles.subtitle}>Tune strategy states, capital bands, and confidence gates.</Text>
      <Text style={styles.summary}>
        {stats.active} active · {stats.paused} paused · avg threshold {stats.avgThreshold}%
      </Text>

      {agents.map((agent) => (
        <AgentCard
          key={agent.id}
          agent={agent}
          onToggle={(enabled) => updateAgent(agent.id, { status: enabled ? "active" : "paused" })}
          onCapitalChange={(assignedCapital) => updateAgent(agent.id, { assignedCapital })}
          onThresholdChange={(confidenceThreshold) => updateAgent(agent.id, { confidenceThreshold })}
        />
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xxl,
    paddingBottom: 120,
  },
  title: {
    color: colors.text,
    fontSize: 32,
    fontFamily: "Inter_800ExtraBold",
    letterSpacing: -0.7,
    marginBottom: spacing.xs,
  },
  subtitle: {
    color: colors.textMuted,
    fontFamily: "Inter_400Regular",
    fontSize: 13,
    marginBottom: spacing.xs,
  },
  summary: {
    alignSelf: "flex-start",
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FFFFFF",
    color: colors.textSoft,
    fontFamily: "Inter_600SemiBold",
    fontSize: 11,
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    marginBottom: spacing.lg,
  },
});
