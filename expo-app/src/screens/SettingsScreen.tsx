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
  } = useTrading();

  const [capitalInput, setCapitalInput] = useState(String(Math.round(capitalLimit)));

  const statusLabel = useMemo(() => {
    if (connectionStatus === "online") return "Online";
    if (connectionStatus === "offline") return "Offline";
    return "Not checked";
  }, [connectionStatus]);

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
            maximumTrackTintColor="#E7E1D4"
            thumbTintColor="#D97706"
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
        trackColor={{ false: "#D6CFBF", true: "#F59E0B" }}
        thumbColor="#FFFFFF"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl,
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
    backgroundColor: "#FFFEFC",
    color: colors.text,
    fontFamily: "Inter_500Medium",
    fontSize: 14,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
  },
  button: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: "#E7B25D",
    backgroundColor: "#FFF4DE",
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
    borderColor: "#E7B25D",
    backgroundColor: "#FFF4DE",
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
    backgroundColor: "#FFFEFC",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
  },
  pressed: {
    transform: [{ scale: 0.98 }],
  },
});
