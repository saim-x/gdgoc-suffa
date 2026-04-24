import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useMemo } from "react";
import { useTrading } from "../context/TradingContext";
import { colorForPnl, colors, radius, spacing } from "../theme";
import { GlassCard } from "../components/GlassCard";
import { TrendChart } from "../components/TrendChart";
import type { SummaryRecord, TrendPeriod } from "../types";

export function PortfolioScreen() {
  const { agents, activeTrades, metrics, trendPeriod, setTrendPeriod, summaryRecords } = useTrading();

  const allocations = useMemo(() => {
    const total = activeTrades.reduce((sum, trade) => sum + trade.positionSize, 0) || 1;
    const byAsset = new Map<string, number>();
    activeTrades.forEach((trade) => {
      byAsset.set(trade.asset, (byAsset.get(trade.asset) ?? 0) + trade.positionSize);
    });
    return [...byAsset.entries()]
      .map(([asset, amount]) => ({ asset, amount, percent: (amount / total) * 100 }))
      .sort((a, b) => b.amount - a.amount);
  }, [activeTrades]);

  const activeAllocated = agents.filter((a) => a.status === "active").reduce((sum, a) => sum + a.assignedCapital, 0);
  const restrictedPct = Math.min(100, (activeAllocated / Math.max(metrics.restrictedCapital, 1)) * 100);
  const activePct = Math.min(100, (metrics.activeCapital / Math.max(metrics.restrictedCapital, 1)) * 100);
  const trendValues = useMemo(() => buildTrendSeries(summaryRecords, trendPeriod), [summaryRecords, trendPeriod]);

  return (
    <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <Text style={styles.title}>Portfolio</Text>
      <Text style={styles.subtitle}>Restricted-capital governance and performance telemetry.</Text>
      <View style={styles.quickStatsRow}>
        <QuickStat label="Open Positions" value={activeTrades.length} />
        <QuickStat label="Tracked Assets" value={allocations.length} />
        <QuickStat label="Closed Trades" value={summaryRecords.length} />
      </View>

      <GlassCard innerStyle={styles.card}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Capital Breakdown</Text>
          <Text style={styles.sectionMeta}>Live utilization bands</Text>
        </View>
        <View style={styles.segmentTrack}>
          <View style={[styles.segmentRestricted, { width: `${restrictedPct}%` }]} />
          <View style={[styles.segmentActive, { width: `${activePct}%` }]} />
        </View>
        <View style={styles.legendRow}>
          <LegendDot color="#5D8A72" label={`Restricted ${metrics.restrictedCapital.toFixed(0)}`} />
          <LegendDot color="#1E9B62" label={`Active ${metrics.activeCapital.toFixed(0)}`} />
        </View>
      </GlassCard>

      <GlassCard innerStyle={styles.card}>
        <View style={styles.periodHeader}>
          <Text style={styles.sectionTitle}>Profit Trend</Text>
          <View style={styles.periodWrap}>
            {(["1D", "1W", "1M"] as TrendPeriod[]).map((period) => {
              const selected = period === trendPeriod;
              return (
                <Pressable
                  key={period}
                  onPress={() => setTrendPeriod(period)}
                  style={({ pressed }) => [styles.periodChip, selected && styles.periodChipSelected, pressed && styles.pressed]}
                >
                  <Text style={[styles.periodText, selected && styles.periodTextSelected]}>{period}</Text>
                </Pressable>
              );
            })}
          </View>
        </View>
        <TrendChart values={trendValues} />
        <Text style={[styles.netPnl, { color: colorForPnl(metrics.totalPnl) }]}>
          Net P/L: {metrics.totalPnl >= 0 ? "+" : ""}
          {metrics.totalPnl.toFixed(2)}
        </Text>
      </GlassCard>

      <GlassCard innerStyle={styles.card}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Asset Allocation</Text>
          <Text style={styles.sectionMeta}>By active position size</Text>
        </View>
        {allocations.length ? (
          allocations.map((item) => (
            <View key={item.asset} style={styles.assetRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.assetName}>{item.asset}</Text>
                <View style={styles.assetBarTrack}>
                  <View style={[styles.assetBarFill, { width: `${item.percent}%` }]} />
                </View>
              </View>
              <Text style={styles.assetValue}>{item.percent.toFixed(1)}%</Text>
            </View>
          ))
        ) : (
          <Text style={styles.empty}>No live allocations yet.</Text>
        )}
      </GlassCard>
    </ScrollView>
  );
}

function QuickStat({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.quickStat}>
      <Text style={styles.quickStatLabel}>{label}</Text>
      <Text style={styles.quickStatValue}>{value}</Text>
    </View>
  );
}

function buildTrendSeries(records: SummaryRecord[], period: TrendPeriod): number[] {
  const now = Date.now();
  const spanDays = period === "1D" ? 1 : period === "1W" ? 7 : 30;
  const minTime = now - spanDays * 24 * 60 * 60 * 1000;

  const filtered = records
    .filter((record) => new Date(record.executed_at).getTime() >= minTime)
    .sort((a, b) => new Date(a.executed_at).getTime() - new Date(b.executed_at).getTime());

  if (!filtered.length) return [0, 0, 0, 0, 0, 0];

  const cumulative: number[] = [];
  let running = 0;
  filtered.forEach((record) => {
    running += record.pnl;
    cumulative.push(Number(running.toFixed(2)));
  });

  if (cumulative.length >= 10) return cumulative.slice(-10);
  const padded = [...cumulative];
  while (padded.length < 6) padded.unshift(padded[0] ?? 0);
  return padded;
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={styles.legendLabel}>{label}</Text>
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
    letterSpacing: -0.8,
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 13,
    fontFamily: "Inter_400Regular",
    marginTop: -4,
    marginBottom: spacing.xs,
  },
  quickStatsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  quickStat: {
    minWidth: 112,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
    gap: 2,
  },
  quickStatLabel: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 10,
  },
  quickStatValue: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 14,
  },
  card: {
    padding: spacing.lg,
    gap: spacing.md,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 17,
    fontFamily: "Inter_700Bold",
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.sm,
  },
  sectionMeta: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 11,
  },
  segmentTrack: {
    height: 20,
    borderRadius: radius.pill,
    backgroundColor: "#E5EFE8",
    overflow: "hidden",
  },
  segmentRestricted: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    backgroundColor: "#5D8A72",
    borderRadius: radius.pill,
  },
  segmentActive: {
    position: "absolute",
    left: 0,
    top: 4,
    bottom: 4,
    backgroundColor: "#1E9B62",
    borderRadius: radius.pill,
  },
  legendRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
  },
  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendLabel: {
    color: colors.textSoft,
    fontFamily: "Inter_500Medium",
    fontSize: 12,
  },
  periodHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: spacing.sm,
  },
  periodWrap: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  periodChip: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
  },
  periodChipSelected: {
    borderColor: "#20A86F",
    backgroundColor: "#EAF8F1",
  },
  periodText: {
    color: colors.textMuted,
    fontFamily: "Inter_600SemiBold",
    fontSize: 11,
  },
  periodTextSelected: {
    color: colors.text,
  },
  netPnl: {
    fontFamily: "Inter_700Bold",
    fontSize: 16,
  },
  assetRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  assetName: {
    color: colors.text,
    fontFamily: "Inter_600SemiBold",
    fontSize: 13,
    marginBottom: 6,
  },
  assetBarTrack: {
    height: 8,
    borderRadius: radius.pill,
    backgroundColor: "#E5EFE8",
    overflow: "hidden",
  },
  assetBarFill: {
    height: 8,
    borderRadius: radius.pill,
    backgroundColor: "#20A86F",
  },
  assetValue: {
    color: colors.textSoft,
    fontFamily: "Inter_600SemiBold",
    fontSize: 12,
    minWidth: 42,
    textAlign: "right",
  },
  empty: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 13,
  },
  pressed: {
    transform: [{ scale: 0.98 }],
  },
});
