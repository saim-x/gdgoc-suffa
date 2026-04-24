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
    borderColor: "rgba(196, 214, 201, 0.55)",
    backgroundColor: "#FFFFFF",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.06,
    shadowRadius: 18,
    elevation: 5,
  },
  inner: {
    borderRadius: radius.lg,
    backgroundColor: "rgba(252, 255, 253, 0.94)",
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.85)",
  },
});
