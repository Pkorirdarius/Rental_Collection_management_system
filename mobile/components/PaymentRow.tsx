import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { Badge } from "./Badge";
import { Card } from "./Card";
import { formatDateTime, formatKES, statusTone } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { Payment } from "@/lib/types";

export function PaymentRow({ payment, onPress }: { payment: Payment; onPress?: () => void }) {
  const mpesa = payment.method.startsWith("MPESA");
  return (
    <Card onPress={onPress} style={styles.card}>
      <View style={[styles.icon, { backgroundColor: mpesa ? colors.successSoft : colors.infoSoft }]}>
        <Ionicons
          name={mpesa ? "phone-portrait-outline" : "cash-outline"}
          size={20}
          color={mpesa ? colors.success : colors.info}
        />
      </View>
      <View style={styles.body}>
        <View style={styles.top}>
          <Text style={styles.name} numberOfLines={1}>
            {payment.tenant_name || "Unmatched payment"}
          </Text>
          <Text style={styles.amount}>{formatKES(payment.amount)}</Text>
        </View>
        <Text style={styles.meta} numberOfLines={1}>
          {payment.property_name ? `${payment.property_name} · ${payment.unit_code}` : "No unit assigned"}
        </Text>
        <View style={styles.bottom}>
          <Text style={styles.reference}>{payment.receipt_number || payment.reference || "—"}</Text>
          <Text style={styles.date}>{formatDateTime(payment.paid_at)}</Text>
        </View>
      </View>
      <Badge label={payment.status} tone={statusTone(payment.status)} />
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  icon: {
    width: 42,
    height: 42,
    borderRadius: radii.md,
    alignItems: "center",
    justifyContent: "center",
  },
  body: { flex: 1, gap: 3 },
  top: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  name: { flex: 1, fontSize: 14, fontWeight: "700", color: colors.text },
  amount: { fontSize: 14, fontWeight: "700", color: colors.text },
  meta: { fontSize: 11, color: colors.textMuted },
  bottom: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.sm },
  reference: { fontSize: 11, color: colors.textMuted, flexShrink: 1 },
  date: { fontSize: 11, color: colors.textMuted },
});
