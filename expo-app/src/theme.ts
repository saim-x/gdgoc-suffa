export const colors = {
  background: "#F7F5F0",
  panel: "#FFFFFF",
  panelRaised: "#FCFBF8",
  border: "#E9E5DC",
  borderStrong: "#DDD6C6",
  text: "#1D1A14",
  textMuted: "#7B7466",
  textSoft: "#9A9385",
  aiBlue: "#D97706",
  aiPurple: "#F59E0B",
  profit: "#1E9B62",
  loss: "#D64545",
  warning: "#D97706",
  tabMuted: "#8E8676",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 18,
  xl: 28,
  xxl: 36,
};

export const radius = {
  sm: 12,
  md: 16,
  lg: 20,
  pill: 999,
};

export const typography = {
  h1: 34,
  h2: 24,
  h3: 18,
  body: 14,
  caption: 12,
};

export function colorForPnl(value: number): string {
  if (value > 0) return colors.profit;
  if (value < 0) return colors.loss;
  return colors.textSoft;
}
