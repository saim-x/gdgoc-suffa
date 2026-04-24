import { Animated, Easing, StyleSheet, Text, View } from "react-native";
import { useEffect, useRef } from "react";
import type { SystemStatus } from "../types";
import { colors, radius, spacing } from "../theme";

type StatusStripProps = {
  status: SystemStatus;
};

export function StatusStrip({ status }: StatusStripProps) {
  const pulse = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 900,
          easing: Easing.bezier(0.22, 1, 0.36, 1),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 900,
          easing: Easing.bezier(0.22, 1, 0.36, 1),
          useNativeDriver: true,
        }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  const dotColor = status === "executing" ? colors.profit : status === "analyzing" ? colors.aiBlue : colors.textMuted;
  const label =
    status === "executing"
      ? "Executing trade"
      : status === "analyzing"
        ? "Analyzing sentiment and market structure"
        : "Scanning markets";

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.dot,
          {
            backgroundColor: dotColor,
            transform: [
              {
                scale: pulse.interpolate({
                  inputRange: [0, 1],
                  outputRange: [1, 1.28],
                }),
              },
            ],
            opacity: pulse.interpolate({
              inputRange: [0, 1],
              outputRange: [0.65, 1],
            }),
          },
        ]}
      />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: "#FEF7ED",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  dot: {
    width: 9,
    height: 9,
    borderRadius: radius.pill,
  },
  label: {
    color: colors.textSoft,
    fontFamily: "Inter_500Medium",
    fontSize: 12,
  },
});
