import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { colors, radii, spacing } from "@/lib/theme";

export type Tone = "success" | "warning" | "danger" | "info" | "neutral";

const tones: Record<Tone, { background: string; text: string }> = {
  success: { background: colors.successSoft, text: colors.success },
  warning: { background: colors.warningSoft, text: colors.warning },
  danger: { background: colors.dangerSoft, text: colors.danger },
  info: { background: colors.infoSoft, text: colors.info },
  neutral: { background: colors.surfaceMuted, text: colors.textMuted },
};

export function Badge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  const palette = tones[tone];
  return (
    <View style={[styles.badge, { backgroundColor: palette.background }]}>
      <Text style={[styles.text, { color: palette.text }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: radii.pill,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 3,
    alignSelf: "flex-start",
  },
  text: { fontSize: 11, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.3 },
});
