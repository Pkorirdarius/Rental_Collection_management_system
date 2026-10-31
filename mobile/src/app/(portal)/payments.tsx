import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Alert, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { PaymentRow } from "@/components/PaymentRow";
import { Screen } from "@/components/Screen";
import { EmptyState, ErrorState, Loading } from "@/components/States";
import { openAuthenticatedPdf } from "@/lib/download";
import { useApi } from "@/lib/useApi";
import { formatKES } from "@/lib/format";
import { colors } from "@/lib/theme";
import type { Payment } from "@/lib/types";

export default function PortalPayments() {
  const payments = useApi<Payment[]>("/portal/me/payments");
  const rows = payments.data ?? [];
  const total = rows.reduce((sum, payment) => sum + Number(payment.amount), 0);

  if (payments.loading && !payments.data) return <Loading label="Loading payments…" />;
  if (payments.error && !payments.data) {
    return (
      <Screen>
        <ErrorState message={payments.error} onRetry={payments.reload} />
      </Screen>
    );
  }

  const openReceipt = async (payment: Payment) => {
    if (!payment.has_receipt) {
      Alert.alert("Receipt pending", "A receipt will be available once the payment is confirmed.");
      return;
    }
    try {
      await openAuthenticatedPdf(
        `/payments/${payment.id}/receipt.pdf`,
        `receipt-${payment.receipt_number || payment.id}.pdf`,
      );
    } catch (err) {
      Alert.alert("Could not open receipt", err instanceof Error ? err.message : "Try again.");
    }
  };

  return (
    <Screen refreshing={payments.loading} onRefresh={payments.reload}>
      <Text style={styles.title}>My payments</Text>

      <Card style={styles.summary}>
        <View>
          <Text style={styles.summaryLabel}>Total paid</Text>
          <Text style={styles.summaryValue}>{formatKES(total)}</Text>
          <Text style={styles.summaryHint}>{rows.length} payments</Text>
        </View>
        <View style={styles.summaryIcon}>
          <Ionicons name="receipt" size={24} color={colors.success} />
        </View>
      </Card>

      {rows.length === 0 ? (
        <EmptyState
          title="No payments yet"
          message="Payments you make will appear here with downloadable receipts."
          icon="receipt-outline"
        />
      ) : (
        rows.map((payment) => (
          <PaymentRow key={payment.id} payment={payment} onPress={() => openReceipt(payment)} />
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 26, fontWeight: "800", color: colors.text },
  summary: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.primaryDark,
  },
  summaryLabel: { fontSize: 12, color: "#C7E7E3", fontWeight: "600" },
  summaryValue: { fontSize: 26, fontWeight: "800", color: colors.white, marginTop: 4 },
  summaryHint: { fontSize: 12, color: "#C7E7E3" },
  summaryIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.14)",
    alignItems: "center",
    justifyContent: "center",
  },
});
