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
    borderColor: colors.borderStrong,
    backgroundColor: "#FDFBF7",
  },
  inner: {
    borderRadius: radius.lg,
    backgroundColor: colors.panel,
    borderWidth: 1,
    borderColor: colors.border,
  },
});
