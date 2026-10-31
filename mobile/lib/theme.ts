export const colors = {
  background: "#F4F6F8",
  surface: "#FFFFFF",
  surfaceMuted: "#EEF2F3",
  primary: "#0F766E",
  primaryDark: "#115E59",
  primarySoft: "#D9F0EC",
  text: "#111827",
  textMuted: "#6B7280",
  border: "#E5E7EB",
  success: "#15803D",
  successSoft: "#DCFCE7",
  warning: "#B45309",
  warningSoft: "#FEF3C7",
  danger: "#B91C1C",
  dangerSoft: "#FEE2E2",
  info: "#1D4ED8",
  infoSoft: "#DBEAFE",
  white: "#FFFFFF",
  black: "#000000",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 28,
};

export const radii = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  pill: 999,
};

export const shadow = {
  shadowColor: "#0F172A",
  shadowOpacity: 0.06,
  shadowRadius: 10,
  shadowOffset: { width: 0, height: 4 },
  elevation: 2,
};

export const typography = {
  title: { fontSize: 26, fontWeight: "700" as const, color: colors.text },
  heading: { fontSize: 20, fontWeight: "700" as const, color: colors.text },
  subheading: { fontSize: 16, fontWeight: "600" as const, color: colors.text },
  body: { fontSize: 15, color: colors.text },
  caption: { fontSize: 12, color: colors.textMuted },
};
