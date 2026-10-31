import { Ionicons } from "@expo/vector-icons";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import React from "react";
import { Alert, Linking, Pressable, StyleSheet, Text, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PaymentRow } from "@/components/PaymentRow";
import { Screen } from "@/components/Screen";
import { SectionTitle } from "@/components/SectionTitle";
import { ErrorState, Loading } from "@/components/States";
import { openAuthenticatedPdf } from "@/lib/download";
import { useApi } from "@/lib/useApi";
import { formatDate, formatKES, statusTone } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { Lease, Paginated, Payment, Tenant } from "@/lib/types";

export default function TenantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const tenantApi = useApi<Tenant>(id ? `/tenants/${id}/` : null);
  const tenant = tenantApi.data;
  const leaseApi = useApi<Lease>(tenant?.active_lease_id ? `/leases/${tenant.active_lease_id}/` : null);
  const payments = useApi<Paginated<Payment>>("/payments/", {
    tenant: id ?? "",
    page_size: 10,
  });

  if (tenantApi.loading && !tenant) return <Loading label="Loading tenant…" />;
  if (tenantApi.error && !tenant) {
    return (
      <Screen edges={["bottom", "left", "right"]}>
        <ErrorState message={tenantApi.error} onRetry={tenantApi.reload} />
      </Screen>
    );
  }
  if (!tenant) return null;

  const lease = leaseApi.data;
  const canPay = Boolean(tenant.active_lease_id);

  const openReceipt = async (payment: Payment) => {
    if (!payment.has_receipt) {
      Alert.alert("No receipt", "This payment does not have a receipt yet.");
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
    <Screen
      edges={["bottom", "left", "right"]}
      refreshing={tenantApi.loading || leaseApi.loading || payments.loading}
      onRefresh={() => {
        tenantApi.reload();
        leaseApi.reload();
        payments.reload();
      }}
    >
      <Stack.Screen options={{ title: tenant.full_name }} />

      <Card style={styles.profile}>
        <Avatar name={tenant.full_name} size={58} />
        <View style={styles.profileBody}>
          <Text style={styles.name}>{tenant.full_name}</Text>
          <Text style={styles.meta}>
            {tenant.unit ? `${tenant.unit.property} · ${tenant.unit.code}` : "No active unit"}
          </Text>
          <View style={styles.profileBadges}>
            {tenant.lease_status ? (
              <Badge label={tenant.lease_status} tone={statusTone(tenant.lease_status)} />
            ) : null}
            <Badge label={tenant.status} tone={tenant.status === "ACTIVE" ? "success" : "neutral"} />
          </View>
        </View>
      </Card>

      <View style={styles.contactRow}>
        <ContactButton
          icon="call-outline"
          label="Call"
          onPress={() => Linking.openURL(`tel:${tenant.phone}`)}
        />
        <ContactButton
          icon="chatbubble-outline"
          label="SMS"
          onPress={() => Linking.openURL(`sms:${tenant.phone}`)}
        />
        <ContactButton
          icon="mail-outline"
          label="Email"
          onPress={() => Linking.openURL(`mailto:${tenant.email}`)}
          disabled={!tenant.email}
        />
      </View>

      <Card style={styles.balanceCard}>
        <View>
          <Text style={styles.balanceLabel}>Outstanding balance</Text>
          <Text style={styles.balanceValue}>{formatKES(tenant.balance)}</Text>
        </View>
        {lease ? (
          <View style={styles.dueBox}>
            <Text style={styles.dueLabel}>Rent due</Text>
            <Text style={styles.dueValue}>Day {lease.due_day}</Text>
            {lease.days_overdue > 0 ? (
              <Text style={styles.overdue}>{lease.days_overdue} days late</Text>
            ) : null}
          </View>
        ) : null}
      </Card>

      <View style={styles.actions}>
        <Button
          label="Record payment"
          icon="add-circle-outline"
          onPress={() =>
            router.push({
              pathname: "/record-payment",
              params: { tenantId: tenant.id, leaseId: tenant.active_lease_id ?? "" },
            })
          }
          disabled={!canPay}
          style={styles.action}
        />
        <Button
          label="Statement"
          icon="document-text-outline"
          variant="secondary"
          onPress={() =>
            router.push({ pathname: "/statement", params: { tenantId: tenant.id } })
          }
          style={styles.action}
        />
      </View>

      <SectionTitle title="Lease" />
      {lease ? (
        <Card style={styles.details}>
          <DetailRow label="Property" value={lease.property_name} />
          <DetailRow label="Unit" value={lease.unit_code} />
          <DetailRow label="Rent" value={formatKES(lease.rent_amount)} />
          <DetailRow label="Start date" value={formatDate(lease.start_date)} />
          <DetailRow label="Due day" value={`Day ${lease.due_day}`} />
          <DetailRow
            label="Deposit"
            value={`${formatKES(lease.deposit_paid)} of ${formatKES(lease.deposit_amount)}`}
          />
          <DetailRow
            label="Status"
            value={lease.payment_status}
            valueColor={lease.payment_status === "OVERDUE" ? colors.danger : colors.text}
          />
        </Card>
      ) : (
        <Card>
          <Text style={styles.muted}>No active lease for this tenant.</Text>
        </Card>
      )}

      <SectionTitle title="Recent payments" />
      {payments.loading && !payments.data ? (
        <Loading label="Loading payments…" />
      ) : payments.data?.results.length ? (
        payments.data.results.map((payment) => (
          <PaymentRow key={payment.id} payment={payment} onPress={() => openReceipt(payment)} />
        ))
      ) : (
        <Card>
          <Text style={styles.muted}>No payments recorded for this tenant yet.</Text>
        </Card>
      )}
    </Screen>
  );
}

function ContactButton({
  icon,
  label,
  onPress,
  disabled = false,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.contact,
        disabled && styles.contactDisabled,
        pressed && styles.contactPressed,
      ]}
    >
      <Ionicons name={icon} size={19} color={disabled ? colors.textMuted : colors.primary} />
      <Text style={[styles.contactLabel, disabled && { color: colors.textMuted }]}>{label}</Text>
    </Pressable>
  );
}

function DetailRow({
  label,
  value,
  valueColor = colors.text,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={[styles.detailValue, { color: valueColor }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  profile: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  profileBody: { flex: 1, gap: 3 },
  name: { fontSize: 19, fontWeight: "800", color: colors.text },
  meta: { fontSize: 12, color: colors.textMuted },
  profileBadges: { flexDirection: "row", gap: spacing.sm, marginTop: 4 },
  contactRow: { flexDirection: "row", gap: spacing.sm },
  contact: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    paddingVertical: spacing.md,
  },
  contactPressed: { backgroundColor: colors.surfaceMuted },
  contactDisabled: { opacity: 0.5 },
  contactLabel: { fontSize: 12, fontWeight: "600", color: colors.primary },
  balanceCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.primaryDark,
  },
  balanceLabel: { fontSize: 12, color: "#C7E7E3", fontWeight: "600" },
  balanceValue: { fontSize: 28, fontWeight: "800", color: colors.white, marginTop: 4 },
  dueBox: { alignItems: "flex-end", gap: 2 },
  dueLabel: { fontSize: 11, color: "#C7E7E3" },
  dueValue: { fontSize: 15, fontWeight: "700", color: colors.white },
  overdue: { fontSize: 11, color: "#FECACA", fontWeight: "600" },
  actions: { flexDirection: "row", gap: spacing.sm },
  action: { flex: 1 },
  details: { gap: spacing.sm },
  detailRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.md },
  detailLabel: { fontSize: 12, color: colors.textMuted },
  detailValue: { fontSize: 13, fontWeight: "600" },
  muted: { fontSize: 13, color: colors.textMuted },
});
