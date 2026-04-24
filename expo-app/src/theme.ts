export const colors = {
  background: "#F6FAF7",
  panel: "#FFFFFF",
  panelRaised: "#F8FCFA",
  border: "#DFEAE3",
  borderStrong: "#CCDCCE",
  text: "#122217",
  textMuted: "#607466",
  textSoft: "#7C9183",
  aiBlue: "#20A86F",
  aiPurple: "#5CCF9D",
  profit: "#1E9B62",
  loss: "#D64545",
  warning: "#5D8A72",
  tabMuted: "#748879",
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
