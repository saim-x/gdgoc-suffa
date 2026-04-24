import { Animated, StyleSheet, Text, View } from "react-native";
import { useEffect, useRef } from "react";
import { colors, radius, spacing } from "../theme";

type TrendChartProps = {
  values: number[];
};

export function TrendChart({ values }: TrendChartProps) {
  const anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(anim, {
      toValue: 1,
      duration: 650,
      useNativeDriver: true,
    }).start();
  }, [anim, values]);

  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;

  return (
    <View style={styles.wrap}>
      <View style={styles.chartRow}>
        {values.map((value, index) => {
          const normalized = (value - min) / range;
          const height = 20 + normalized * 88;
          return (
            <Animated.View
              key={`${value}-${index}`}
              style={[
                styles.bar,
                {
                  height,
                  opacity: anim,
                  transform: [
                    {
                      translateY: anim.interpolate({
                        inputRange: [0, 1],
                        outputRange: [10, 0],
                      }),
                    },
                  ],
                },
              ]}
            />
          );
        })}
      </View>
      <View style={styles.metaRow}>
        <Text style={styles.meta}>Low</Text>
        <Text style={styles.meta}>Trend</Text>
        <Text style={styles.meta}>High</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#FCFBF8",
    padding: spacing.md,
    gap: spacing.sm,
  },
  chartRow: {
    minHeight: 120,
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 6,
  },
  bar: {
    flex: 1,
    borderRadius: radius.pill,
    backgroundColor: "#D97706",
  },
  metaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  meta: {
    color: colors.textMuted,
    fontSize: 11,
    fontFamily: "Inter_500Medium",
  },
});
