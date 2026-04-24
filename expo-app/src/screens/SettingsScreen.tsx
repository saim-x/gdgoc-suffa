import { Alert, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from "react-native";
import Slider from "@react-native-community/slider";
import { useMemo, useState } from "react";
import { useTrading } from "../context/TradingContext";
import { colors, radius, spacing } from "../theme";
import type { RiskLevel } from "../types";
import { GlassCard } from "../components/GlassCard";

const riskLevels: RiskLevel[] = ["low", "medium", "high"];

export function SettingsScreen() {
  const {
    apiUrl,
    setApiUrl,
    connectionStatus,
    pingBackend,
    checkingConnection,
    autonomousMode,
    setAutonomousMode,
    riskLevel,
    setRiskLevel,
    biometricLock,
    setBiometricLock,
    notificationsEnabled,
    setNotificationsEnabled,
    capitalLimit,
    setCapitalLimit,
    defaultConfidenceThreshold,
    setDefaultConfidenceThreshold,
    resetAllTradingData,
    resettingData,
  } = useTrading();

  const [capitalInput, setCapitalInput] = useState(String(Math.round(capitalLimit)));

  const statusLabel = useMemo(() => {
    if (connectionStatus === "online") return "Online";
    if (connectionStatus === "offline") return "Offline";
    return "Not checked";
  }, [connectionStatus]);

  const onResetData = () => {
    Alert.alert(
      "Delete all trading data?",
      "This removes trades, signals, pending approvals, activity, and daily summaries on the server. Portfolio capital and agent assignments return to defaults so you can test again.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete everything",
          style: "destructive",
          onPress: () => void resetAllTradingData(),
        },
      ]
    );
  };

  const onAutonomousToggle = (next: boolean) => {
    if (!next) {
      setAutonomousMode(false);
      return;
    }
    Alert.alert(
      "Enable autonomous mode?",
      "Agents may execute medium-confidence trades without waiting for approval.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Enable", style: "destructive", onPress: () => setAutonomousMode(true) },
      ]
    );
  };

  return (
    <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <Text style={styles.title}>Settings</Text>
      <Text style={styles.subtitle}>Risk controls, thresholds, security, and device preferences.</Text>
      <View style={styles.metaRow}>
        <View style={styles.metaChip}>
          <Text style={styles.metaChipLabel}>API</Text>
          <Text style={[styles.metaChipValue, connectionStatus === "online" && { color: colors.profit }]}>{statusLabel}</Text>
        </View>
        <View style={styles.metaChip}>
          <Text style={styles.metaChipLabel}>Mode</Text>
          <Text style={styles.metaChipValue}>{autonomousMode ? "Autonomous" : "Approval"}</Text>
        </View>
        <View style={styles.metaChip}>
          <Text style={styles.metaChipLabel}>Risk</Text>
          <Text style={styles.metaChipValue}>{riskLevel.toUpperCase()}</Text>
        </View>
      </View>

      <GlassCard innerStyle={styles.card}>
        <Text style={styles.sectionTitle}>Connection</Text>
        <TextInput
          style={styles.input}
          value={apiUrl}
          onChangeText={setApiUrl}
          placeholder="API URL"
          placeholderTextColor={colors.textMuted}
          autoCapitalize="none"
        />
        <View style={styles.row}>
          <Pressable style={({ pressed }) => [styles.button, pressed && styles.pressed]} onPress={pingBackend}>
            <Text style={styles.buttonText}>{checkingConnection ? "Checking..." : "Ping API"}</Text>
          </Pressable>
          <Text style={[styles.connectionText, connectionStatus === "online" && { color: colors.profit }]}>
            {statusLabel}
          </Text>
        </View>
      </GlassCard>

      <GlassCard innerStyle={styles.card}>
        <Text style={styles.sectionTitle}>Risk Management</Text>
        <View style={styles.field}>
          <Text style={styles.label}>Total Capital Limit</Text>
          <TextInput
            style={styles.input}
            value={capitalInput}
            keyboardType="numeric"
            onChangeText={(text) => {
              setCapitalInput(text);
              const parsed = Number(text);
              if (Number.isFinite(parsed) && parsed > 0) setCapitalLimit(parsed);
            }}
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Default confidence threshold: {Math.round(defaultConfidenceThreshold)}%</Text>
          <Slider
            minimumValue={60}
            maximumValue={95}
            step={1}
            value={defaultConfidenceThreshold}
            onValueChange={setDefaultConfidenceThreshold}
            minimumTrackTintColor={colors.aiBlue}
            maximumTrackTintColor="#DCE9E1"
            thumbTintColor="#20A86F"
          />
        </View>

        <View style={styles.riskRow}>
          {riskLevels.map((level) => {
            const active = level === riskLevel;
            return (
              <Pressable
                key={level}
                onPress={() => setRiskLevel(level)}
                style={({ pressed }) => [styles.riskChip, active && styles.riskChipActive, pressed && styles.pressed]}
              >
                <Text style={[styles.riskText, active && styles.riskTextActive]}>{level.toUpperCase()}</Text>
              </Pressable>
            );
          })}
        </View>
      </GlassCard>

      <GlassCard innerStyle={styles.card}>
        <Text style={styles.sectionTitle}>Automation & Security</Text>
        <SettingSwitch label="Autonomous mode" value={autonomousMode} onValueChange={onAutonomousToggle} />
        <SettingSwitch label="Notifications" value={notificationsEnabled} onValueChange={setNotificationsEnabled} />
        <SettingSwitch label="Biometric lock" value={biometricLock} onValueChange={setBiometricLock} />
      </GlassCard>

      <GlassCard innerStyle={styles.card}>
        <Text style={styles.sectionTitle}>Data</Text>
        <Text style={styles.hint}>
          Server-side only. Use when simulated capital is stuck so agents can trade again.
        </Text>
        <Pressable
          style={({ pressed }) => [styles.dangerButton, pressed && styles.pressed]}
          onPress={onResetData}
          disabled={resettingData}
        >
          <Text style={styles.dangerButtonText}>{resettingData ? "Resetting…" : "Reset all trading data"}</Text>
        </Pressable>
      </GlassCard>
    </ScrollView>
  );
}

function SettingSwitch({
  label,
  value,
  onValueChange,
}: {
  label: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
}) {
  return (
    <View style={styles.switchRow}>
      <Text style={styles.label}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onValueChange}
        trackColor={{ false: "#C8D8CD", true: "#20A86F" }}
        thumbColor="#FFFFFF"
      />
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
  metaRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  metaChip: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  metaChipLabel: {
    color: colors.textMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 10,
  },
  metaChipValue: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 11,
  },
  card: {
    padding: spacing.lg,
    gap: spacing.md,
  },
  sectionTitle: {
    color: colors.text,
    fontFamily: "Inter_700Bold",
    fontSize: 17,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  field: {
    gap: spacing.sm,
  },
  label: {
    color: colors.textSoft,
    fontSize: 13,
    fontFamily: "Inter_500Medium",
  },
  input: {
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FFFFFF",
    color: colors.text,
    fontFamily: "Inter_500Medium",
    fontSize: 14,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
  },
  button: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: "#20A86F",
    backgroundColor: "#EAF8F1",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  buttonText: {
    color: colors.text,
    fontSize: 12,
    fontFamily: "Inter_600SemiBold",
  },
  connectionText: {
    color: colors.textMuted,
    fontFamily: "Inter_600SemiBold",
    fontSize: 12,
  },
  riskRow: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  riskChip: {
    flex: 1,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.sm,
    alignItems: "center",
  },
  riskChipActive: {
    borderColor: "#20A86F",
    backgroundColor: "#EAF8F1",
  },
  riskText: {
    color: colors.textMuted,
    fontSize: 11,
    fontFamily: "Inter_600SemiBold",
  },
  riskTextActive: {
    color: colors.text,
  },
  switchRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
  },
  pressed: {
    transform: [{ scale: 0.98 }],
  },
  hint: {
    color: colors.textMuted,
    fontSize: 12,
    fontFamily: "Inter_400Regular",
    lineHeight: 17,
  },
  dangerButton: {
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: "#C94C4C",
    backgroundColor: "#FCECEC",
    paddingVertical: spacing.md,
    alignItems: "center",
  },
  dangerButtonText: {
    color: "#A32E2E",
    fontFamily: "Inter_600SemiBold",
    fontSize: 14,
  },
});
