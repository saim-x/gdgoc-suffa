import { ScrollView, StyleSheet, Text } from "react-native";
import { useTrading } from "../context/TradingContext";
import { colors, spacing } from "../theme";
import { AgentCard } from "../components/AgentCard";

export function AgentsScreen() {
  const { agents, updateAgent } = useTrading();

  return (
    <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <Text style={styles.title}>Agents</Text>
      <Text style={styles.subtitle}>Tune strategy states, capital bands, and confidence gates.</Text>

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
    marginBottom: spacing.lg,
  },
});
