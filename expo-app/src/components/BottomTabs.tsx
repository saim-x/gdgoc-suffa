import { Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, radius, spacing } from "../theme";

export type TabKey = "home" | "portfolio" | "agents" | "activity" | "settings";

type TabItem = {
  key: TabKey;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
};

const tabs: TabItem[] = [
  { key: "home", label: "Home", icon: "home-outline" },
  { key: "portfolio", label: "Portfolio", icon: "pie-chart-outline" },
  { key: "agents", label: "Agents", icon: "hardware-chip-outline" },
  { key: "activity", label: "Activity", icon: "pulse-outline" },
  { key: "settings", label: "Settings", icon: "settings-outline" },
];

type BottomTabsProps = {
  activeTab: TabKey;
  onChange: (tab: TabKey) => void;
};

export function BottomTabs({ activeTab, onChange }: BottomTabsProps) {
  return (
    <View style={styles.shell}>
      <View style={styles.inner}>
        {tabs.map((tab) => {
          const active = tab.key === activeTab;
          return (
            <Pressable
              key={tab.key}
              onPress={() => onChange(tab.key)}
              style={({ pressed }) => [styles.item, pressed && styles.pressed, active && styles.activeItem]}
            >
              <Ionicons name={tab.icon} size={18} color={active ? colors.text : colors.tabMuted} />
              <Text style={[styles.label, active && styles.activeLabel]}>{tab.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  shell: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
    paddingTop: spacing.sm,
    backgroundColor: "transparent",
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
  },
  inner: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: "rgba(212, 226, 217, 0.9)",
    backgroundColor: "rgba(250, 255, 252, 0.96)",
    padding: 4,
    flexDirection: "row",
    justifyContent: "space-between",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.08,
    shadowRadius: 24,
    elevation: 8,
  },
  item: {
    flex: 1,
    borderRadius: radius.pill,
    paddingVertical: spacing.sm,
    alignItems: "center",
    justifyContent: "center",
    gap: 2,
  },
  activeItem: {
    backgroundColor: "rgba(32,168,111,0.17)",
  },
  label: {
    color: colors.tabMuted,
    fontFamily: "Inter_500Medium",
    fontSize: 10,
  },
  activeLabel: {
    color: "#11472F",
  },
  pressed: {
    transform: [{ scale: 0.98 }],
  },
});
