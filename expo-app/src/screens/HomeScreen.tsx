import { useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useTrading } from "../context/TradingContext";
import { colorForPnl, colors, radius, spacing } from "../theme";
import { GlassCard } from "../components/GlassCard";
import { MetricBox } from "../components/MetricBox";
import { SignalCard } from "../components/SignalCard";
import { StatusStrip } from "../components/StatusStrip";
import { TrendChart } from "../components/TrendChart";
import type { TrendPeriod } from "../types";

export function HomeScreen() {
  const {
    mainAgent,
    updateAgent,
    connectionStatus,
    systemStatus,
    metrics,
    portfolio,
    demoMode,
    pendingTrades,
    resolvePendingTrade,
    recentSignals,
    activeTrades,
    activity,
    pastTrades,
    pnlSeries,
    confidenceSeries,
    trendPeriod,
    setTrendPeriod,
    buildDailySummary,
    dailySummary,
  } = useTrading();

  const statusColor = connectionStatus === "online" ? colors.profit : colors.loss;
  const statusLabel = connectionStatus === "online" ? "API live" : "API offline";

  const agentStatusLabel = mainAgent.status === "active" ? "Live" : "Paused";

  const usedCapital = useMemo(
    () => activeTrades.reduce((sum, trade) => sum + trade.positionSize, 0),
    [activeTrades]
  );
  const executedCount = useMemo(() => activity.filter((item) => item.type === "executed").length, [activity]);
  const [chartMode, setChartMode] = useState<"pnl" | "confidence">("pnl");

  const usedPct = useMemo(() => {
    const denom = Math.max(mainAgent.assignedCapital, 1);
    return Math.min(999, (usedCapital / denom) * 100);
  }, [usedCapital, mainAgent.assignedCapital]);

  const totalReturnPct = useMemo(() => {
    const denom = Math.max(portfolio?.totalCapital ?? 0, 1);
    return (metrics.totalPnl / denom) * 100;
  }, [metrics.totalPnl, portfolio?.totalCapital]);

  const profitTrend = useMemo(() => normalizeSeries(pnlSeries, trendPeriod), [pnlSeries, trendPeriod]);
  const confTrend = useMemo(() => normalizeSeries(confidenceSeries, trendPeriod), [confidenceSeries, trendPeriod]);

  const displayTotalPnl = demoMode ? Math.abs(metrics.totalPnl) : metrics.totalPnl;
  const displayTotalReturnPct = demoMode ? Math.abs(totalReturnPct) : totalReturnPct;
  const mainAgentPendingTrades = useMemo(
    () =>
      pendingTrades
        .filter((trade) => trade.agentId === mainAgent.id)
        .sort((a, b) => {
          const expiryOrder = a.expiresAt - b.expiresAt;
          if (expiryOrder !== 0) return expiryOrder;
          return b.confidence - a.confidence;
        }),
    [pendingTrades, mainAgent.id]
  );
  const visiblePendingTrades = mainAgentPendingTrades.slice(0, 6);
  const actionableSignals = useMemo(() => recentSignals.filter((signal) => signal.action !== "hold"), [recentSignals]);
  const recentActivity = useMemo(() => activity.slice(0, 6), [activity]);
  const recentPastTrades = useMemo(() => {
    const unique = Array.from(
      new Map(
        pastTrades.map((trade) => [
          trade.trade_id ?? `${trade.symbol}-${trade.executed_at}-${trade.position_size}`,
          trade,
        ])
      ).values()
    );
    return unique.slice(0, 8);
  }, [pastTrades]);
  const latestSignalTimestamp = actionableSignals[0]?.timestamp ?? recentSignals[0]?.timestamp ?? null;

  return (
    <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <GlassCard innerStyle={styles.heroCard}>
        <View style={styles.heroTop}>
          <LinearGradient colors={["#5CCF9D", "#20A86F"]} style={styles.mascotOrb}>
            <Text style={styles.mascotText}>ORION</Text>
          </LinearGradient>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>ORION Autonomous Console</Text>
            <Text style={styles.subtitle}>Live signal parsing, adaptive execution, and guardrail-protected approvals.</Text>
          </View>
        </View>

        <View style={styles.statusRow}>
          <View style={styles.badge}>
            <View style={[styles.dot, { backgroundColor: statusColor }]} />
            <Text style={styles.badgeText}>{statusLabel}</Text>
          </View>
          <View style={styles.badge}>
            <View style={[styles.dot, { backgroundColor: mainAgent.status === "active" ? colors.profit : colors.warning }]} />
            <Text style={styles.badgeText}>{agentStatusLabel}</Text>
          </View>
        </View>

        <StatusStrip status={systemStatus} />
      </GlassCard>

      <View style={styles.metricsGrid}>
        <MetricBox
          label="Total P/L"
          value={`${displayTotalPnl >= 0 ? "+" : ""}${displayTotalPnl.toFixed(2)}`}
          delta={demoMode ? "Recording view" : displayTotalPnl >= 0 ? "Net positive" : "Net negative"}
          deltaValue={demoMode ? 1 : displayTotalPnl}
        />
        <MetricBox
          label="Total Return"
          value={`${displayTotalReturnPct >= 0 ? "+" : ""}${displayTotalReturnPct.toFixed(2)}%`}
          delta="Against total capital"
          deltaValue={demoMode ? 1 : displayTotalReturnPct}
        />
        <MetricBox
          label="Today's P/L"
          value={`${metrics.todayPnl >= 0 ? "+" : ""}${metrics.todayPnl.toFixed(2)}`}
          delta={metrics.todayPnl >= 0 ? "Today up" : "Today down"}
          deltaValue={metrics.todayPnl}
        />
        <MetricBox label="Trades Executed" value={`${executedCount}`} delta="Progress logged" deltaValue={1} />
        <MetricBox
          label="Used / Limit"
          value={`${usedCapital.toFixed(0)} / ${mainAgent.assignedCapital.toFixed(0)}`}
          delta={`${usedPct.toFixed(1)}% utilized`}
          deltaValue={1}
        />
      </View>

      <GlassCard innerStyle={styles.sectionCard}>
        <View style={styles.periodHeader}>
          <Text style={styles.sectionTitle}>Telemetry</Text>
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

        <View style={styles.bandWrap}>
          <View style={styles.bandTrack}>
            <View style={[styles.bandRestricted, { width: `${Math.min(100, usedPct)}%` }]} />
            <View style={[styles.bandUsed, { width: `${Math.min(100, usedPct)}%` }]} />
          </View>
          <View style={styles.bandLegend}>
            <Text style={styles.bandLabel}>Limit {mainAgent.assignedCapital.toFixed(0)}</Text>
            <Text style={styles.bandLabel}>Used {usedCapital.toFixed(0)}</Text>
          </View>
        </View>

        <View style={styles.modeRow}>
          <Pressable
            onPress={() => setChartMode("pnl")}
            style={({ pressed }) => [styles.modeChip, chartMode === "pnl" && styles.modeChipSelected, pressed && styles.pressed]}
          >
            <Text style={[styles.modeText, chartMode === "pnl" && styles.modeTextSelected]}>P/L Trend</Text>
          </Pressable>
          <Pressable
            onPress={() => setChartMode("confidence")}
            style={({ pressed }) => [
              styles.modeChip,
              chartMode === "confidence" && styles.modeChipSelected,
              pressed && styles.pressed,
            ]}
          >
            <Text style={[styles.modeText, chartMode === "confidence" && styles.modeTextSelected]}>Signal Confidence</Text>
          </Pressable>
        </View>

        <TrendChart values={chartMode === "pnl" ? profitTrend : confTrend} />
        <Text style={styles.sectionMeta}>
          {chartMode === "pnl"
            ? `Cumulative closed-trade P/L (${profitTrend.length} samples)`
            : `Last ${Math.min(10, recentSignals.length)} signal confidence scores`}
        </Text>
      </GlassCard>

      <GlassCard innerStyle={styles.sectionCard}>
        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>Autonomy Controls</Text>
          <Text style={styles.sectionMeta}>Risk & capital boundaries</Text>
        </View>
        <Text style={styles.runtimeDescription}>
          ORION is continuously scanning the watchlist, scoring confidence, opening positions, and requesting your approval when
          confidence is mid-band.
        </Text>
        <View style={styles.heartbeatGrid}>
          <View style={styles.heartbeatCell}>
            <Text style={styles.heartbeatLabel}>Last signal</Text>
            <Text style={styles.heartbeatValue}>
              {latestSignalTimestamp ? new Date(latestSignalTimestamp).toLocaleTimeString() : "Waiting"}
            </Text>
          </View>
          <View style={styles.heartbeatCell}>
            <Text style={styles.heartbeatLabel}>Actionable signals</Text>
            <Text style={styles.heartbeatValue}>{actionableSignals.length}</Text>
          </View>
          <View style={styles.heartbeatCell}>
            <Text style={styles.heartbeatLabel}>Open positions</Text>
            <Text style={styles.heartbeatValue}>{activeTrades.length}</Text>
          </View>
          <View style={styles.heartbeatCell}>
            <Text style={styles.heartbeatLabel}>Awaiting approvals</Text>
            <Text style={styles.heartbeatValue}>{mainAgentPendingTrades.length}</Text>
          </View>
        </View>
        <View style={styles.rowButtons}>
          <ActionButton
            label={mainAgent.status === "active" ? "Pause Agent" : "Set Agent Live"}
            onPress={() => updateAgent(mainAgent.id, { status: mainAgent.status === "active" ? "paused" : "active" })}
            secondary
          />
          <ActionButton label="Generate Daily Brief" onPress={buildDailySummary} />
        </View>
      </GlassCard>

      <GlassCard innerStyle={styles.sectionCard}>
        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>Autonomous Activity Feed</Text>
          <Text style={styles.sectionMeta}>{recentActivity.length} recent events</Text>
        </View>
        {recentActivity.length ? (
          recentActivity.map((item) => (
            <View key={item.id} style={styles.feedRow}>
              <View
                style={[
                  styles.feedBadge,
                  item.type === "executed"
                    ? styles.feedBadgeExecuted
                    : item.type === "pending"
                      ? styles.feedBadgePending
                      : styles.feedBadgeRejected,
                ]}
              >
                <Text style={styles.feedBadgeText}>{item.type.toUpperCase()}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.feedTitle}>
                  {item.asset} · {item.action.toUpperCase()} · {item.confidence}%
                </Text>
                <Text style={styles.feedMeta}>
                  {new Date(item.timestamp).toLocaleTimeString()} · {item.note}
                </Text>
              </View>
            </View>
          ))
        ) : (
          <Text style={styles.empty}>No activity yet. ORION is warming up.</Text>
        )}
      </GlassCard>

      <GlassCard innerStyle={styles.sectionCardNoRight}>
        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>Signal Radar</Text>
          <Text style={styles.sectionMeta}>Directional opportunities</Text>
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingRight: spacing.sm }}>
          {actionableSignals.length ? (
            actionableSignals.map((signal) => <SignalCard key={signal.id} signal={signal} />)
          ) : (
            <Text style={styles.empty}>No actionable signals yet.</Text>
          )}
        </ScrollView>
      </GlassCard>

      <GlassCard innerStyle={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Pending Trade Confirmations · ORION</Text>
        {visiblePendingTrades.length ? (
          visiblePendingTrades.map((trade) => (
            <View key={trade.id} style={styles.pendingRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.pendingAsset}>
                  {trade.symbol} · {trade.suggestedAction.toUpperCase()}
                </Text>
                <Text style={styles.pendingMeta}>
                  {trade.confidence}% confidence · {Math.max(0, Math.ceil((trade.expiresAt - Date.now()) / 1000))}s
                </Text>
              </View>
              <ActionButton label="Reject" onPress={() => resolvePendingTrade(trade.id, false)} tiny secondary />
              <ActionButton label="Accept" onPress={() => resolvePendingTrade(trade.id, true)} tiny />
            </View>
          ))
        ) : (
          <Text style={styles.empty}>No pending confirmations.</Text>
        )}
        {mainAgentPendingTrades.length > visiblePendingTrades.length ? (
          <Text style={styles.sectionMeta}>
            Showing {visiblePendingTrades.length} of {mainAgentPendingTrades.length} pending approvals.
          </Text>
        ) : null}
      </GlassCard>

      <GlassCard innerStyle={styles.sectionCard}>
        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>Past Trades</Text>
          <Text style={styles.sectionMeta}>{recentPastTrades.length} closed positions</Text>
        </View>
        {recentPastTrades.length ? (
          recentPastTrades.map((trade) => (
            <View key={trade.trade_id ?? `${trade.executed_at}-${trade.symbol}-${trade.position_size}`} style={styles.tradeRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.tradeAsset}>{trade.symbol}</Text>
                <Text style={styles.tradeMeta}>
                  Closed {new Date(trade.executed_at).toLocaleString()} · size {trade.position_size.toFixed(2)}
                </Text>
              </View>
              <Text style={[styles.tradePnl, { color: colorForPnl(trade.pnl) }]}>
                {trade.pnl >= 0 ? "+" : ""}
                {trade.pnl.toFixed(2)}
              </Text>
            </View>
          ))
        ) : (
          <Text style={styles.empty}>No executed trades yet.</Text>
        )}
      </GlassCard>

      {dailySummary ? (
        <GlassCard innerStyle={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Daily Summary ({dailySummary.date})</Text>
          <Text style={styles.summaryMeta}>
            Executed {dailySummary.trades_executed} · Win rate {dailySummary.win_rate.toFixed(1)}% · Net{" "}
            {dailySummary.total_pnl.toFixed(2)}
          </Text>
        </GlassCard>
      ) : null}
    </ScrollView>
  );
}

function ActionButton({
  label,
  onPress,
  secondary,
  tiny,
}: {
  label: string;
  onPress: () => void;
  secondary?: boolean;
  tiny?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        secondary && styles.buttonSecondary,
        tiny && styles.buttonTiny,
        pressed && styles.pressed,
      ]}
    >
      <Text style={[styles.buttonText, secondary && styles.buttonTextSecondary]}>{label}</Text>
    </Pressable>
  );
}

function normalizeSeries(values: number[], period: TrendPeriod): number[] {
  const cap = period === "1D" ? 18 : period === "1W" ? 24 : 30;
  const sliced = values.slice(-cap);
  if (sliced.length >= 10) return sliced.slice(-10);
  const padded = [...sliced];
  while (padded.length < 6) padded.unshift(padded[0] ?? 0);
  return padded.length ? padded : [0, 0, 0, 0, 0, 0];
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xxl + spacing.sm,
    paddingBottom: 130,
    gap: spacing.lg,
  },
  heroCard: {
    padding: spacing.lg,
    gap: spacing.md,
  },
  heroTop: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  mascotOrb: {
    width: 78,
    height: 78,
    borderRadius: 39,
    alignItems: "center",
    justifyContent: "center",
  },
  mascotText: {
    color: "#0D3A27",
    fontFamily: "Inter_700Bold",
    fontSize: 12,
  },
  title: {
    color: colors.text,
    fontSize: 24,
    fontFamily: "Inter_700Bold",
  },
  subtitle: {
    marginTop: 4,
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 20,
    fontFamily: "Inter_400Regular",
  },
  statusRow: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    backgroundColor: "#F6FCF8",
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  badgeText: {
    color: colors.textMuted,
    fontSize: 11,
    fontFamily: "Inter_600SemiBold",
  },
  metricsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
  },
  sectionCard: {
    padding: spacing.lg,
    gap: spacing.sm,
  },
  sectionCardNoRight: {
    paddingVertical: spacing.lg,
    paddingLeft: spacing.lg,
    paddingRight: 0,
    gap: spacing.sm,
  },
  sectionHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  periodHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: spacing.sm,
  },
  periodWrap: {
    flexDirection: "row",
    gap: 6,
  },
  periodChip: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 10,
    paddingVertical: 7,
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
    color: "#0D6A45",
  },
  modeRow: {
    flexDirection: "row",
    gap: spacing.sm,
    flexWrap: "wrap",
  },
  modeChip: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: spacing.sm,
    paddingVertical: 8,
  },
  modeChipSelected: {
    borderColor: colors.borderStrong,
    backgroundColor: "#F2FAF6",
  },
  modeText: {
    color: colors.textMuted,
    fontFamily: "Inter_600SemiBold",
    fontSize: 11,
  },
  modeTextSelected: {
    color: colors.text,
  },
  bandWrap: {
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  bandTrack: {
    height: 10,
    borderRadius: radius.pill,
    backgroundColor: "#EEF5F1",
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
  },
  bandRestricted: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    backgroundColor: "#D6E6DD",
  },
  bandUsed: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    backgroundColor: "#20A86F",
    opacity: 0.9,
  },
  bandLegend: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  bandLabel: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 11,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 17,
    fontFamily: "Inter_700Bold",
  },
  sectionMeta: {
    color: colors.textMuted,
    fontSize: 11,
    fontFamily: "Inter_500Medium",
  },
  runtimeDescription: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 12,
    lineHeight: 18,
  },
  heartbeatGrid: {
    marginTop: spacing.xs,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  heartbeatCell: {
    minWidth: 132,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: "#FBFEFC",
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
    gap: 4,
  },
  heartbeatLabel: {
    color: colors.textSoft,
    fontFamily: "Inter_500Medium",
    fontSize: 11,
  },
  heartbeatValue: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 15,
  },
  feedRow: {
    flexDirection: "row",
    gap: spacing.sm,
    alignItems: "flex-start",
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    paddingVertical: spacing.sm,
  },
  feedBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  feedBadgeExecuted: {
    backgroundColor: "#E8F7EF",
  },
  feedBadgePending: {
    backgroundColor: "#FFF7E2",
  },
  feedBadgeRejected: {
    backgroundColor: "#FDECEC",
  },
  feedBadgeText: {
    fontSize: 10,
    fontFamily: "Inter_700Bold",
    color: colors.text,
  },
  feedTitle: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 12,
  },
  feedMeta: {
    marginTop: 2,
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 11,
  },
  inlineInputs: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  inputWrap: {
    flex: 1,
    gap: 5,
  },
  inputLabel: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FFFFFF",
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    color: colors.text,
    fontFamily: "Inter_500Medium",
  },
  inputMultiline: {
    minHeight: 76,
    textAlignVertical: "top",
  },
  sourceRow: {
    flexDirection: "row",
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  sourceChip: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingVertical: 10,
    alignItems: "center",
    backgroundColor: "#FFFFFF",
  },
  sourceActive: {
    borderColor: "#20A86F",
    backgroundColor: "#EAF8F1",
  },
  sourceText: {
    color: colors.textMuted,
    fontFamily: "Inter_600SemiBold",
    fontSize: 12,
  },
  sourceTextActive: {
    color: "#0D6A45",
  },
  rowButtons: {
    flexDirection: "row",
    gap: spacing.sm,
    flexWrap: "wrap",
  },
  button: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: "#1A8F5E",
    backgroundColor: "#20A86F",
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  buttonSecondary: {
    borderColor: colors.borderStrong,
    backgroundColor: "#F2FAF6",
  },
  buttonText: {
    color: "#FFFFFF",
    fontFamily: "Inter_600SemiBold",
    fontSize: 12,
  },
  buttonTextSecondary: {
    color: colors.text,
  },
  buttonTiny: {
    paddingVertical: 7,
    paddingHorizontal: spacing.sm,
  },
  pendingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    paddingVertical: spacing.sm,
  },
  pendingAsset: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 13,
  },
  pendingMeta: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 11,
    marginTop: 2,
  },
  tradeRow: {
    flexDirection: "row",
    gap: spacing.md,
    alignItems: "center",
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    paddingVertical: spacing.sm,
  },
  tradeAsset: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 13,
  },
  tradeMeta: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 11,
  },
  tradePnl: {
    fontFamily: "Inter_700Bold",
    fontSize: 12,
  },
  summaryMeta: {
    color: colors.textSoft,
    fontFamily: "Inter_500Medium",
    fontSize: 13,
  },
  empty: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 12,
    paddingVertical: spacing.sm,
  },
  pressed: {
    transform: [{ scale: 0.98 }],
  },
});
