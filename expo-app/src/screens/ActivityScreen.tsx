import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useMemo } from "react";
import { useTrading } from "../context/TradingContext";
import { colorForPnl, colors, radius, spacing } from "../theme";
import type { ActivityFilter } from "../types";
import { GlassCard } from "../components/GlassCard";

const filters: ActivityFilter[] = ["all", "executed", "pending", "rejected"];

export function ActivityScreen() {
  const { activity, activityFilter, setActivityFilter, filteredActivity } = useTrading();
  const stats = useMemo(() => {
    return {
      total: activity.length,
      executed: activity.filter((item) => item.type === "executed").length,
      pending: activity.filter((item) => item.type === "pending").length,
      rejected: activity.filter((item) => item.type === "rejected").length,
    };
  }, [activity]);

  return (
    <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <Text style={styles.title}>Activity</Text>
      <Text style={styles.subtitle}>Execution log and confidence-driven decision trail.</Text>

      <View style={styles.statsRow}>
        <StatChip label="Total" value={stats.total} />
        <StatChip label="Executed" value={stats.executed} />
        <StatChip label="Pending" value={stats.pending} />
        <StatChip label="Rejected" value={stats.rejected} />
      </View>

      <View style={styles.filterRow}>
        {filters.map((filter) => {
          const active = filter === activityFilter;
          return (
            <Pressable
              key={filter}
              onPress={() => setActivityFilter(filter)}
              style={({ pressed }) => [styles.filterChip, active && styles.filterChipActive, pressed && styles.pressed]}
            >
              <Text style={[styles.filterText, active && styles.filterTextActive]}>{filter.toUpperCase()}</Text>
            </Pressable>
          );
        })}
      </View>

      <GlassCard innerStyle={styles.feedCard}>
        {filteredActivity.length ? (
          filteredActivity.map((item) => (
            <View key={item.id} style={styles.feedItem}>
              <View style={{ flex: 1 }}>
                <View style={styles.feedTop}>
                  <View style={styles.feedTopLeft}>
                    <Text style={styles.asset}>{item.asset}</Text>
                    <View
                      style={[
                        styles.typePill,
                        item.type === "executed"
                          ? styles.typePillExecuted
                          : item.type === "pending"
                            ? styles.typePillPending
                            : styles.typePillRejected,
                      ]}
                    >
                      <Text style={styles.typePillText}>{item.type.toUpperCase()}</Text>
                    </View>
                  </View>
                  <Text style={styles.time}>
                    {new Date(item.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </Text>
                </View>
                <Text style={styles.meta}>
                  {item.action.toUpperCase()} · {item.confidence}% confidence
                </Text>
                <Text style={styles.note} numberOfLines={2}>
                  {item.note}
                </Text>
              </View>
              <Text style={[styles.pnl, { color: colorForPnl(item.pnl) }]}>
                {item.pnl >= 0 ? "+" : ""}
                {item.pnl.toFixed(2)}
              </Text>
            </View>
          ))
        ) : (
          <Text style={styles.empty}>No events in this filter yet.</Text>
        )}
      </GlassCard>
    </ScrollView>
  );
}

function StatChip({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.statChip}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xxl,
    paddingBottom: 120,
    gap: spacing.md,
  },
  title: {
    color: colors.text,
    fontSize: 32,
    fontFamily: "Inter_800ExtraBold",
    letterSpacing: -0.7,
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 13,
    fontFamily: "Inter_400Regular",
    marginTop: -6,
  },
  statsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  statChip: {
    minWidth: 78,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: spacing.sm,
    paddingVertical: 7,
    gap: 2,
  },
  statLabel: {
    color: colors.textMuted,
    fontSize: 10,
    fontFamily: "Inter_500Medium",
  },
  statValue: {
    color: colors.text,
    fontSize: 13,
    fontFamily: "Inter_700Bold",
  },
  filterRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  filterChip: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.sm,
    paddingVertical: 7,
  },
  filterChipActive: {
    borderColor: "#20A86F",
    backgroundColor: "#EAF8F1",
  },
  filterText: {
    color: colors.textMuted,
    fontSize: 11,
    fontFamily: "Inter_600SemiBold",
  },
  filterTextActive: {
    color: colors.text,
  },
  feedCard: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  feedItem: {
    flexDirection: "row",
    gap: spacing.md,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    alignItems: "flex-start",
  },
  feedTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  feedTopLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  asset: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 14,
  },
  typePill: {
    borderRadius: radius.pill,
    paddingHorizontal: 7,
    paddingVertical: 3,
  },
  typePillExecuted: {
    backgroundColor: "#E8F7EF",
  },
  typePillPending: {
    backgroundColor: "#FFF7E2",
  },
  typePillRejected: {
    backgroundColor: "#FDECEC",
  },
  typePillText: {
    fontSize: 9,
    color: colors.text,
    fontFamily: "Inter_700Bold",
  },
  time: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 11,
  },
  meta: {
    color: colors.textSoft,
    fontFamily: "Inter_600SemiBold",
    fontSize: 12,
    marginTop: 2,
  },
  note: {
    color: colors.textMuted,
    fontFamily: "Inter_400Regular",
    fontSize: 12,
    marginTop: spacing.xs,
  },
  pnl: {
    fontFamily: "Inter_700Bold",
    fontSize: 13,
    minWidth: 60,
    textAlign: "right",
    marginTop: 2,
  },
  empty: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 13,
    paddingVertical: spacing.xl,
  },
  pressed: {
    transform: [{ scale: 0.98 }],
  },
});
