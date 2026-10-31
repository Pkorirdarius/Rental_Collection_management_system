import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { colors, radii, spacing } from "@/lib/theme";

interface StatCardProps {
  label: string;
  value: string;
  hint?: string;
  icon: keyof typeof Ionicons.glyphMap;
  tone?: "primary" | "success" | "warning" | "danger";
}

const toneColors = {
  primary: { background: colors.primarySoft, foreground: colors.primary },
  success: { background: colors.successSoft, foreground: colors.success },
  warning: { background: colors.warningSoft, foreground: colors.warning },
  danger: { background: colors.dangerSoft, foreground: colors.danger },
};

export function StatCard({ label, value, hint, icon, tone = "primary" }: StatCardProps) {
  const palette = toneColors[tone];
  return (
    <View style={styles.card}>
      <View style={[styles.iconWrap, { backgroundColor: palette.background }]}>
        <Ionicons name={icon} size={18} color={palette.foreground} />
      </View>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value} numberOfLines={1} adjustsFontSizeToFit>
        {value}
      </Text>
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minWidth: "45%",
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    gap: 6,
  },
  iconWrap: {
    width: 34,
    height: 34,
    borderRadius: radii.md,
    alignItems: "center",
    justifyContent: "center",
  },
  label: { fontSize: 12, color: colors.textMuted, fontWeight: "600" },
  value: { fontSize: 20, fontWeight: "700", color: colors.text },
  hint: { fontSize: 11, color: colors.textMuted },
});
