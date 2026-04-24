import { useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useTrading } from "../context/TradingContext";
import { colorForPnl, colors, radius, spacing } from "../theme";
import { GlassCard } from "../components/GlassCard";
import { MetricBox } from "../components/MetricBox";
import { SignalCard } from "../components/SignalCard";
import { StatusStrip } from "../components/StatusStrip";
import type { SignalDraft } from "../types";

const defaultDraft: SignalDraft = {
  source: "x",
  author: "Donald Trump",
  symbol: "TSLA",
  content: "New tariff policy announced for EV battery imports.",
};

export function HomeScreen() {
  const {
    mainAgent,
    updateAgent,
    connectionStatus,
    systemStatus,
    analyzeSignal,
    analyzing,
    metrics,
    pendingTrades,
    resolvePendingTrade,
    recentSignals,
    activeTrades,
    pastTrades,
    buildDailySummary,
    dailySummary,
  } = useTrading();

  const [draft, setDraft] = useState<SignalDraft>(defaultDraft);
  const statusColor = connectionStatus === "online" ? colors.profit : colors.loss;
  const statusLabel = connectionStatus === "online" ? "API live" : "API offline";

  const agentStatusLabel = mainAgent.status === "active" ? "Live" : "Paused";

  const usedCapital = useMemo(
    () => activeTrades.reduce((sum, trade) => sum + trade.positionSize, 0),
    [activeTrades]
  );

  return (
    <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <GlassCard innerStyle={styles.heroCard}>
        <View style={styles.heroTop}>
          <LinearGradient colors={["#FCD34D", "#F59E0B"]} style={styles.mascotOrb}>
            <Text style={styles.mascotText}>ORION</Text>
          </LinearGradient>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>Main Agent Console</Text>
            <Text style={styles.subtitle}>Limits-first autonomous trading with human approvals in the loop.</Text>
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
          value={`${metrics.totalPnl >= 0 ? "+" : ""}${metrics.totalPnl.toFixed(2)}`}
          delta={metrics.totalPnl >= 0 ? "Net positive" : "Net negative"}
          deltaValue={metrics.totalPnl}
        />
        <MetricBox
          label="Today's P/L"
          value={`${metrics.todayPnl >= 0 ? "+" : ""}${metrics.todayPnl.toFixed(2)}`}
          delta={metrics.todayPnl >= 0 ? "Today up" : "Today down"}
          deltaValue={metrics.todayPnl}
        />
        <MetricBox label="Agent Limit" value={mainAgent.assignedCapital.toFixed(0)} />
        <MetricBox label="Used Capital" value={usedCapital.toFixed(0)} />
      </View>

      <GlassCard innerStyle={styles.sectionCard}>
        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>Main Agent Setup</Text>
          <Text style={styles.sectionMeta}>Live workflow controls</Text>
        </View>
        <View style={styles.inlineInputs}>
          <InputBox
            label="Agent Limit"
            value={String(mainAgent.assignedCapital)}
            onChangeText={(value) => {
              const parsed = Number(value);
              if (Number.isFinite(parsed) && parsed > 0) {
                updateAgent(mainAgent.id, { assignedCapital: parsed });
              }
            }}
          />
          <InputBox
            label="Threshold %"
            value={String(mainAgent.confidenceThreshold)}
            onChangeText={(value) => {
              const parsed = Number(value);
              if (Number.isFinite(parsed)) {
                updateAgent(mainAgent.id, { confidenceThreshold: Math.max(60, Math.min(95, parsed)) });
              }
            }}
          />
        </View>
        <View style={styles.rowButtons}>
          <ActionButton
            label={mainAgent.status === "active" ? "Pause Agent" : "Set Agent Live"}
            onPress={() => updateAgent(mainAgent.id, { status: mainAgent.status === "active" ? "paused" : "active" })}
            secondary
          />
        </View>
      </GlassCard>

      <GlassCard innerStyle={styles.sectionCard}>
        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>Signal Input</Text>
          <Text style={styles.sectionMeta}>POST /truth/analyze</Text>
        </View>
        <View style={styles.sourceRow}>
          <SourceChip active={draft.source === "x"} label="X" onPress={() => setDraft((prev) => ({ ...prev, source: "x" }))} />
          <SourceChip
            active={draft.source === "truth_social"}
            label="Truth Social"
            onPress={() => setDraft((prev) => ({ ...prev, source: "truth_social" }))}
          />
        </View>
        <InputBox label="Author" value={draft.author} onChangeText={(author) => setDraft((prev) => ({ ...prev, author }))} />
        <InputBox
          label="Asset"
          value={draft.symbol}
          onChangeText={(symbol) => setDraft((prev) => ({ ...prev, symbol: symbol.toUpperCase() }))}
        />
        <InputBox
          label="Announcement"
          value={draft.content}
          multiline
          onChangeText={(content) => setDraft((prev) => ({ ...prev, content }))}
        />
        <View style={styles.rowButtons}>
          <ActionButton label={analyzing ? "Analyzing..." : "Run Analysis"} onPress={() => analyzeSignal(draft)} />
          <ActionButton label="Daily Summary" onPress={buildDailySummary} secondary />
        </View>
      </GlassCard>

      <GlassCard innerStyle={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Pending Trade Confirmations</Text>
        {pendingTrades.length ? (
          pendingTrades.map((trade) => (
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
      </GlassCard>

      <GlassCard innerStyle={styles.sectionCardNoRight}>
        <Text style={styles.sectionTitle}>Recent Signals</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingRight: spacing.sm }}>
          {recentSignals.length ? (
            recentSignals.map((signal) => <SignalCard key={signal.id} signal={signal} />)
          ) : (
            <Text style={styles.empty}>No signal responses yet.</Text>
          )}
        </ScrollView>
      </GlassCard>

      <GlassCard innerStyle={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Past Trades</Text>
        {pastTrades.length ? (
          pastTrades.slice(0, 8).map((trade) => (
            <View key={`${trade.executed_at}-${trade.symbol}`} style={styles.tradeRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.tradeAsset}>{trade.symbol}</Text>
                <Text style={styles.tradeMeta}>
                  {new Date(trade.executed_at).toLocaleString()} · size {trade.position_size.toFixed(2)}
                </Text>
              </View>
              <Text style={[styles.tradePnl, { color: colorForPnl(trade.pnl) }]}>{trade.pnl.toFixed(2)}</Text>
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

function InputBox({
  label,
  value,
  onChangeText,
  multiline,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  multiline?: boolean;
}) {
  return (
    <View style={styles.inputWrap}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        style={[styles.input, multiline && styles.inputMultiline]}
        placeholderTextColor={colors.textSoft}
        multiline={multiline}
      />
    </View>
  );
}

function SourceChip({ active, label, onPress }: { active: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.sourceChip, active && styles.sourceActive, pressed && styles.pressed]}>
      <Text style={[styles.sourceText, active && styles.sourceTextActive]}>{label}</Text>
    </Pressable>
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

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl,
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
    color: "#522503",
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
    backgroundColor: "#FFFCF6",
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
    backgroundColor: "#FFFEFC",
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
    backgroundColor: "#FFFEFC",
  },
  sourceActive: {
    borderColor: "#F59E0B",
    backgroundColor: "#FFF4DE",
  },
  sourceText: {
    color: colors.textMuted,
    fontFamily: "Inter_600SemiBold",
    fontSize: 12,
  },
  sourceTextActive: {
    color: "#8A4B0B",
  },
  rowButtons: {
    flexDirection: "row",
    gap: spacing.sm,
    flexWrap: "wrap",
  },
  button: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: "#E7B25D",
    backgroundColor: "#F59E0B",
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  buttonSecondary: {
    borderColor: colors.borderStrong,
    backgroundColor: "#FFF8EC",
  },
  buttonText: {
    color: "#4A2500",
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
