import { StyleSheet, View, type ViewStyle } from "react-native";
import { colors, radius } from "../theme";

type GlassCardProps = {
  children: React.ReactNode;
  style?: ViewStyle;
  innerStyle?: ViewStyle;
};

export function GlassCard({ children, style, innerStyle }: GlassCardProps) {
  return (
    <View style={[styles.shell, style]}>
      <View style={[styles.inner, innerStyle]}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  shell: {
    borderRadius: radius.lg + 2,
    padding: 1.5,
    borderWidth: 1,
    borderColor: "rgba(204, 220, 206, 0.4)", // Softer border
    backgroundColor: "#FFFFFF",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.04,
    shadowRadius: 12,
    elevation: 2,
  },
  inner: {
    borderRadius: radius.lg,
    backgroundColor: "rgba(255, 255, 255, 0.8)", // Glassy look
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.5)",
  },
});
