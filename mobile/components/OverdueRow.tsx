import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { Badge } from "./Badge";
import { Card } from "./Card";
import { formatKES, statusTone } from "@/lib/format";
import { colors, spacing } from "@/lib/theme";
import type { OverdueTenant } from "@/lib/types";

export function OverdueRow({
  row,
  onPress,
}: {
  row: OverdueTenant;
  onPress?: () => void;
}) {
  return (
    <Card onPress={onPress} style={styles.card}>
      <View style={styles.left}>
        <Text style={styles.name} numberOfLines={1}>
          {row.tenant}
        </Text>
        <Text style={styles.meta} numberOfLines={1}>
          {row.property} · {row.unit}
        </Text>
        <View style={styles.days}>
          <Ionicons name="time-outline" size={12} color={colors.danger} />
          <Text style={styles.daysText}>{row.days_overdue} days overdue</Text>
        </View>
      </View>
      <View style={styles.right}>
        <Text style={styles.amount}>{formatKES(row.balance)}</Text>
        <Badge label={row.status} tone={statusTone(row.status)} />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  left: { flex: 1, gap: 3 },
  right: { alignItems: "flex-end", gap: 6 },
  name: { fontSize: 14, fontWeight: "700", color: colors.text },
  meta: { fontSize: 11, color: colors.textMuted },
  days: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 2 },
  daysText: { fontSize: 11, color: colors.danger, fontWeight: "600" },
  amount: { fontSize: 14, fontWeight: "700", color: colors.text },
});
