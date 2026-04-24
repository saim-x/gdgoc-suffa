import { SafeAreaView, StyleSheet, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { useMemo, useState } from "react";
import { TradingProvider } from "./context/TradingContext";
import { BottomTabs, type TabKey } from "./components/BottomTabs";
import { HomeScreen } from "./screens/HomeScreen";
import { PortfolioScreen } from "./screens/PortfolioScreen";
import { AgentsScreen } from "./screens/AgentsScreen";
import { ActivityScreen } from "./screens/ActivityScreen";
import { SettingsScreen } from "./screens/SettingsScreen";
import { colors } from "./theme";

function AppLayout() {
  const [tab, setTab] = useState<TabKey>("home");

  const screen = useMemo(() => {
    if (tab === "portfolio") return <PortfolioScreen />;
    if (tab === "agents") return <AgentsScreen />;
    if (tab === "activity") return <ActivityScreen />;
    if (tab === "settings") return <SettingsScreen />;
    return <HomeScreen />;
  }, [tab]);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="dark" />
      <View style={styles.bg}>
        <View style={styles.glowA} pointerEvents="none" />
        <View style={styles.glowB} pointerEvents="none" />
        <View style={styles.content}>{screen}</View>
        <BottomTabs activeTab={tab} onChange={setTab} />
      </View>
    </SafeAreaView>
  );
}

export function TradingApp() {
  return (
    <TradingProvider>
      <AppLayout />
    </TradingProvider>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
  },
  bg: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
  glowA: {
    position: "absolute",
    top: -120,
    right: -100,
    width: 300,
    height: 300,
    borderRadius: 150,
    backgroundColor: "rgba(32,168,111,0.08)",
  },
  glowB: {
    position: "absolute",
    bottom: 120,
    left: -120,
    width: 250,
    height: 250,
    borderRadius: 125,
    backgroundColor: "rgba(92,207,157,0.06)",
  },
});
