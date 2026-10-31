import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useMemo, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PaymentRow } from "@/components/PaymentRow";
import { Screen } from "@/components/Screen";
import { ErrorState, Loading } from "@/components/States";
import { useApi } from "@/lib/useApi";
import { formatKES, formatNumber } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { Paginated, Payment } from "@/lib/types";

type Filter = "ALL" | "CASH" | "MPESA" | "UNMATCHED";

const filters: { key: Filter; label: string }[] = [
  { key: "ALL", label: "All" },
  { key: "CASH", label: "Cash" },
  { key: "MPESA", label: "M-Pesa" },
  { key: "UNMATCHED", label: "Unmatched" },
];

export default function PaymentsScreen() {
  const router = useRouter();
  const { data, loading, error, reload } = useApi<Paginated<Payment>>("/payments/", {
    page_size: 100,
  });
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("ALL");

  const payments = useMemo(() => data?.results ?? [], [data]);
  const thisMonth = new Date().toISOString().slice(0, 7);
  const monthTotal = payments
    .filter((payment) => payment.paid_at.startsWith(thisMonth))
    .reduce((sum, payment) => sum + Number(payment.amount), 0);

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return payments.filter((payment) => {
      const matchesSearch =
        !term ||
        (payment.tenant_name ?? "").toLowerCase().includes(term) ||
        (payment.receipt_number ?? "").toLowerCase().includes(term) ||
        (payment.reference ?? "").toLowerCase().includes(term);
      const matchesFilter =
        filter === "ALL" ||
        (filter === "CASH" && payment.method === "CASH") ||
        (filter === "MPESA" && payment.method.startsWith("MPESA")) ||
        (filter === "UNMATCHED" && payment.status === "UNMATCHED");
      return matchesSearch && matchesFilter;
    });
  }, [payments, search, filter]);

  const openPayment = (payment: Payment) => {
    if (payment.tenant) {
      router.push(`/tenant/${payment.tenant}`);
      return;
    }
    Alert.alert(
      "Unmatched payment",
      `${formatKES(payment.amount)}\nReference: ${payment.reference || "—"}\nBill ref: ${
        payment.bill_ref || "—"
      }\n\nMatch it from the web dashboard.`,
    );
  };

  if (loading && !data) return <Loading label="Loading payments…" />;
  if (error && !data) {
    return (
      <Screen>
        <ErrorState message={error} onRetry={reload} />
      </Screen>
    );
  }

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <View style={styles.heading}>
        <View>
          <Text style={styles.title}>Payments</Text>
          <Text style={styles.subtitle}>{formatNumber(payments.length)} recent transactions</Text>
        </View>
        <Button
          label="Record"
          icon="add"
          size="sm"
          onPress={() => router.push("/record-payment")}
        />
      </View>

      <Card style={styles.summary}>
        <View>
          <Text style={styles.summaryLabel}>Received this month</Text>
          <Text style={styles.summaryValue}>{formatKES(monthTotal)}</Text>
        </View>
        <View style={styles.summaryIcon}>
          <Ionicons name="trending-up" size={24} color={colors.success} />
        </View>
      </Card>

      <View style={styles.search}>
        <Ionicons name="search" size={18} color={colors.textMuted} />
        <TextInput
          value={search}
          onChangeText={setSearch}
          placeholder="Search tenant or reference"
          placeholderTextColor={colors.textMuted}
          style={styles.searchInput}
          autoCapitalize="none"
          returnKeyType="search"
        />
      </View>

      <View style={styles.filters}>
        {filters.map((item) => {
          const active = filter === item.key;
          return (
            <Pressable
              key={item.key}
              onPress={() => setFilter(item.key)}
              style={[styles.filter, active && styles.filterActive]}
            >
              <Text style={[styles.filterText, active && styles.filterTextActive]}>
                {item.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {visible.length === 0 ? (
        <View style={styles.empty}>
          <Ionicons name="wallet-outline" size={36} color={colors.textMuted} />
          <Text style={styles.emptyTitle}>No payments found</Text>
          <Text style={styles.emptyText}>Record a payment or change the filter.</Text>
        </View>
      ) : (
        visible.map((payment) => (
          <PaymentRow key={payment.id} payment={payment} onPress={() => openPayment(payment)} />
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  heading: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  title: { fontSize: 26, fontWeight: "800", color: colors.text },
  subtitle: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  summary: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.primaryDark,
  },
  summaryLabel: { fontSize: 12, color: "#C7E7E3", fontWeight: "600" },
  summaryValue: { fontSize: 26, fontWeight: "800", color: colors.white, marginTop: 4 },
  summaryIcon: {
    width: 48,
    height: 48,
    borderRadius: radii.md,
    backgroundColor: "rgba(255,255,255,0.14)",
    alignItems: "center",
    justifyContent: "center",
  },
  search: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
  },
  searchInput: { flex: 1, paddingVertical: 12, fontSize: 14, color: colors.text },
  filters: { flexDirection: "row", gap: spacing.sm, flexWrap: "wrap" },
  filter: {
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
  },
  filterActive: { backgroundColor: colors.primary },
  filterText: { fontSize: 12, fontWeight: "600", color: colors.textMuted },
  filterTextActive: { color: colors.white },
  empty: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.xxl },
  emptyTitle: { fontSize: 16, fontWeight: "700", color: colors.text },
  emptyText: { fontSize: 13, color: colors.textMuted },
});
