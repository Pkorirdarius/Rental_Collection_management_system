import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { OverdueRow } from "@/components/OverdueRow";
import { Screen } from "@/components/Screen";
import { SectionTitle } from "@/components/SectionTitle";
import { StatCard } from "@/components/StatCard";
import { ErrorState, Loading } from "@/components/States";
import { TenantRow } from "@/components/TenantRow";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { formatKES, formatNumber, monthLabel } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { DashboardSummary, OverdueTenant, Paginated, Payment, Tenant } from "@/lib/types";

export default function AdminHome() {
  const { user } = useAuth();
  return user?.role === "CARETAKER" ? <CaretakerHome /> : <AdminHomeContent />;
}

function Greeting() {
  const { user } = useAuth();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  return (
    <View style={styles.header}>
      <View style={styles.headerText}>
        <Text style={styles.greeting}>{greeting},</Text>
        <Text style={styles.name} numberOfLines={1}>
          {user?.full_name ?? "Manager"}
        </Text>
        <Text style={styles.org} numberOfLines={1}>
          {user?.organization_name || "Rent Manager"}
        </Text>
      </View>
      <Avatar name={user?.full_name ?? "RM"} size={48} />
    </View>
  );
}

function AdminHomeContent() {
  const router = useRouter();
  const summary = useApi<DashboardSummary>("/dashboard/summary");
  const overdue = useApi<OverdueTenant[]>("/dashboard/overdue");

  if (summary.loading && !summary.data) return <Loading label="Loading dashboard…" />;
  if (summary.error && !summary.data) {
    return (
      <Screen>
        <ErrorState message={summary.error} onRetry={summary.reload} />
      </Screen>
    );
  }
  const data = summary.data;
  if (!data) return null;
  const rate = Math.max(0, Math.min(100, Math.round(data.collection_rate * 100)));

  return (
    <Screen
      refreshing={summary.loading || overdue.loading}
      onRefresh={() => {
        summary.reload();
        overdue.reload();
      }}
    >
      <Greeting />

      <Card style={styles.collectionCard}>
        <View style={styles.collectionTop}>
          <View>
            <Text style={styles.cardLabel}>Collected in {monthLabel(data.month)}</Text>
            <Text style={styles.collectionValue}>{formatKES(data.collected)}</Text>
            <Text style={styles.cardHint}>of {formatKES(data.expected)} expected</Text>
          </View>
          <View style={styles.rateBadge}>
            <Text style={styles.rateValue}>{rate}%</Text>
            <Text style={styles.rateLabel}>collected</Text>
          </View>
        </View>
        <View style={styles.track}>
          <View style={[styles.fill, { width: `${rate}%` }]} />
        </View>
        <View style={styles.statusRow}>
          <StatusChip label="Paid" value={data.status_counts.PAID} tone="success" />
          <StatusChip label="Partial" value={data.status_counts.PARTIAL} tone="warning" />
          <StatusChip label="Overdue" value={data.status_counts.OVERDUE} tone="danger" />
        </View>
      </Card>

      <View style={styles.grid}>
        <StatCard
          label="Outstanding"
          value={formatKES(data.arrears)}
          hint="Total arrears"
          icon="alert-circle-outline"
          tone="danger"
        />
        <StatCard
          label="Active tenants"
          value={formatNumber(data.active_tenants)}
          hint={`${data.active_leases} leases`}
          icon="people-outline"
        />
        <StatCard
          label="Occupancy"
          value={`${Math.round(data.occupancy_rate * 100)}%`}
          hint={`${data.occupied_units} of ${data.units} units`}
          icon="business-outline"
          tone="success"
        />
        <StatCard
          label="Unmatched"
          value={formatNumber(data.unmatched_payments)}
          hint={`${data.open_promises} promises open`}
          icon="help-buoy-outline"
          tone="warning"
        />
      </View>

      <View style={styles.actions}>
        <Button
          label="Record payment"
          icon="add-circle-outline"
          onPress={() => router.push("/record-payment")}
          style={styles.actionButton}
        />
        <Button
          label="Tenants"
          icon="people-outline"
          variant="secondary"
          onPress={() => router.push("/tenants")}
          style={styles.actionButton}
        />
      </View>

      <SectionTitle
        title="Needs attention"
        action={
          <Text style={styles.link} onPress={() => router.push("/tenants")}>
            View all
          </Text>
        }
      />
      {overdue.loading && !overdue.data ? (
        <Loading label="Checking arrears…" />
      ) : overdue.data && overdue.data.length > 0 ? (
        overdue.data
          .slice(0, 5)
          .map((row) => (
            <OverdueRow
              key={row.lease_id}
              row={row}
              onPress={() => router.push(`/tenant/${row.tenant_id}`)}
            />
          ))
      ) : (
        <Card>
          <View style={styles.emptyRow}>
            <Ionicons name="checkmark-circle" size={22} color={colors.success} />
            <Text style={styles.emptyText}>No overdue tenants. Nice work.</Text>
          </View>
        </Card>
      )}
    </Screen>
  );
}

function CaretakerHome() {
  const router = useRouter();
  const tenants = useApi<Paginated<Tenant>>("/tenants/", { page_size: 100 });
  const payments = useApi<Paginated<Payment>>("/payments/", { page_size: 5 });

  if (tenants.loading && !tenants.data) return <Loading label="Loading your portfolio…" />;
  if (tenants.error && !tenants.data) {
    return (
      <Screen>
        <ErrorState message={tenants.error} onRetry={tenants.reload} />
      </Screen>
    );
  }
  const rows = tenants.data?.results ?? [];
  const outstanding = rows.reduce((sum, tenant) => sum + Number(tenant.balance ?? 0), 0);

  return (
    <Screen
      refreshing={tenants.loading || payments.loading}
      onRefresh={() => {
        tenants.reload();
        payments.reload();
      }}
    >
      <Greeting />

      <View style={styles.grid}>
        <StatCard
          label="Assigned tenants"
          value={formatNumber(rows.length)}
          icon="people-outline"
        />
        <StatCard
          label="Outstanding"
          value={formatKES(outstanding)}
          icon="alert-circle-outline"
          tone="danger"
        />
      </View>

      <Button
        label="Record payment"
        icon="add-circle-outline"
        onPress={() => router.push("/record-payment")}
      />

      <SectionTitle title="Recent payments" />
      {payments.data?.results.length ? (
        payments.data.results.map((payment) => (
          <Card key={payment.id} style={styles.recentPayment}>
            <View style={styles.recentLeft}>
              <Text style={styles.recentName}>{payment.tenant_name || "Unmatched"}</Text>
              <Text style={styles.recentMeta}>
                {payment.receipt_number || payment.reference || "No reference"}
              </Text>
            </View>
            <Text style={styles.recentAmount}>{formatKES(payment.amount)}</Text>
          </Card>
        ))
      ) : (
        <Text style={styles.muted}>No payments recorded yet.</Text>
      )}

      <SectionTitle title="My tenants" />
      {rows.map((tenant) => (
        <TenantRow
          key={tenant.id}
          tenant={tenant}
          onPress={() => router.push(`/tenant/${tenant.id}`)}
        />
      ))}
    </Screen>
  );
}

function StatusChip({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "success" | "warning" | "danger";
}) {
  return (
    <View style={styles.chip}>
      <Badge label={label} tone={tone} />
      <Text style={styles.chipValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  headerText: { flex: 1, gap: 2 },
  greeting: { fontSize: 13, color: colors.textMuted },
  name: { fontSize: 22, fontWeight: "800", color: colors.text },
  org: { fontSize: 12, color: colors.textMuted },
  collectionCard: { gap: spacing.md, backgroundColor: colors.primaryDark },
  collectionTop: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md },
  cardLabel: { fontSize: 12, color: "#C7E7E3", fontWeight: "600" },
  collectionValue: { fontSize: 27, fontWeight: "800", color: colors.white, marginTop: 4 },
  cardHint: { fontSize: 12, color: "#C7E7E3" },
  rateBadge: {
    backgroundColor: "rgba(255,255,255,0.14)",
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    alignItems: "center",
    alignSelf: "flex-start",
  },
  rateValue: { fontSize: 20, fontWeight: "800", color: colors.white },
  rateLabel: { fontSize: 10, color: "#C7E7E3" },
  track: { height: 8, borderRadius: radii.pill, backgroundColor: "rgba(255,255,255,0.2)" },
  fill: { height: 8, borderRadius: radii.pill, backgroundColor: "#5EEAD4" },
  statusRow: { flexDirection: "row", gap: spacing.sm },
  chip: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.xs,
  },
  chipValue: { color: colors.white, fontWeight: "700", fontSize: 14 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.md },
  actions: { flexDirection: "row", gap: spacing.sm },
  actionButton: { flex: 1 },
  link: { color: colors.primary, fontSize: 13, fontWeight: "700" },
  emptyRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  emptyText: { color: colors.textMuted, fontSize: 13 },
  muted: { color: colors.textMuted, fontSize: 13 },
  recentPayment: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  recentLeft: { flex: 1, gap: 2 },
  recentName: { fontSize: 14, fontWeight: "600", color: colors.text },
  recentMeta: { fontSize: 11, color: colors.textMuted },
  recentAmount: { fontSize: 14, fontWeight: "700", color: colors.text },
});
