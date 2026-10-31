import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PaymentRow } from "@/components/PaymentRow";
import { Screen } from "@/components/Screen";
import { SectionTitle } from "@/components/SectionTitle";
import { ErrorState, Loading } from "@/components/States";
import { useApi } from "@/lib/useApi";
import { formatKES, statusTone } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { Payment, PortalProfile } from "@/lib/types";

export default function PortalHome() {
  const router = useRouter();
  const profile = useApi<PortalProfile>("/portal/me");
  const payments = useApi<Payment[]>("/portal/me/payments");

  if (profile.loading && !profile.data) return <Loading label="Loading your account…" />;
  if (profile.error && !profile.data) {
    return (
      <Screen>
        <ErrorState message={profile.error} onRetry={profile.reload} />
      </Screen>
    );
  }
  const data = profile.data;
  if (!data) return null;
  const overdue = data.status === "OVERDUE" || data.days_overdue > 0;

  return (
    <Screen
      refreshing={profile.loading || payments.loading}
      onRefresh={() => {
        profile.reload();
        payments.reload();
      }}
    >
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={styles.greeting}>Hello,</Text>
          <Text style={styles.name} numberOfLines={1}>
            {data.full_name}
          </Text>
          <Text style={styles.unit} numberOfLines={1}>
            {data.property ? `${data.property} · ${data.unit}` : "No active tenancy"}
          </Text>
        </View>
        <Avatar name={data.full_name} size={48} />
      </View>

      <Card style={[styles.balanceCard, overdue && styles.balanceOverdue]}>
        <View style={styles.balanceTop}>
          <View>
            <Text style={styles.balanceLabel}>Rent balance</Text>
            <Text style={styles.balanceValue}>{formatKES(data.balance)}</Text>
            <Text style={styles.balanceHint}>
              {overdue ? `${data.days_overdue} days overdue` : "You are up to date"}
            </Text>
          </View>
          <Badge label={data.status} tone={statusTone(data.status)} />
        </View>
        {data.rent_amount ? (
          <View style={styles.rentRow}>
            <Text style={styles.rentLabel}>Monthly rent</Text>
            <Text style={styles.rentValue}>{formatKES(data.rent_amount)}</Text>
            <Text style={styles.rentLabel}>· Due day {data.due_day}</Text>
          </View>
        ) : null}
        <Button
          label="Pay with M-Pesa"
          icon="phone-portrait-outline"
          onPress={() => router.push("/portal-pay")}
          disabled={!data.lease_id}
        />
      </Card>

      <View style={styles.quickRow}>
        <QuickAction
          icon="document-text-outline"
          label="Statement"
          onPress={() => router.push("/portal-statement")}
        />
        <QuickAction
          icon="receipt-outline"
          label="Receipts"
          onPress={() => router.push("/payments")}
        />
        <QuickAction
          icon="call-outline"
          label="Call office"
          onPress={() => router.push("/profile")}
        />
      </View>

      <Card style={styles.payInfo}>
        <View style={styles.payInfoHeader}>
          <Ionicons name="information-circle-outline" size={18} color={colors.info} />
          <Text style={styles.payInfoTitle}>How to pay</Text>
        </View>
        <Text style={styles.payInfoText}>
          Use the M-Pesa button to receive a payment prompt on your phone. You can also pay via
          Paybill using your bill reference.
        </Text>
        {data.bill_ref ? (
          <View style={styles.billRow}>
            <Text style={styles.billLabel}>Bill reference</Text>
            <Text style={styles.billValue}>{data.bill_ref}</Text>
          </View>
        ) : null}
      </Card>

      <SectionTitle title="Recent payments" />
      {payments.loading && !payments.data ? (
        <Loading label="Loading payments…" />
      ) : payments.data && payments.data.length > 0 ? (
        payments.data
          .slice(0, 3)
          .map((payment) => <PaymentRow key={payment.id} payment={payment} />)
      ) : (
        <Card>
          <Text style={styles.muted}>No payments yet. Your receipts will appear here.</Text>
        </Card>
      )}
    </Screen>
  );
}

function QuickAction({
  icon,
  label,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <Card onPress={onPress} style={styles.quick}>
      <View style={styles.quickIcon}>
        <Ionicons name={icon} size={20} color={colors.primary} />
      </View>
      <Text style={styles.quickLabel}>{label}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  headerText: { flex: 1, gap: 2 },
  greeting: { fontSize: 13, color: colors.textMuted },
  name: { fontSize: 22, fontWeight: "800", color: colors.text },
  unit: { fontSize: 12, color: colors.textMuted },
  balanceCard: { gap: spacing.md, backgroundColor: colors.primaryDark },
  balanceOverdue: { backgroundColor: "#7F1D1D" },
  balanceTop: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  balanceLabel: { fontSize: 12, color: "#F3D6D6", fontWeight: "600" },
  balanceValue: { fontSize: 30, fontWeight: "800", color: colors.white, marginTop: 4 },
  balanceHint: { fontSize: 12, color: "#F3D6D6" },
  rentRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  rentLabel: { fontSize: 12, color: "#F3D6D6" },
  rentValue: { fontSize: 13, fontWeight: "700", color: colors.white },
  quickRow: { flexDirection: "row", gap: spacing.sm },
  quick: { flex: 1, alignItems: "center", gap: spacing.sm, paddingVertical: spacing.lg },
  quickIcon: {
    width: 40,
    height: 40,
    borderRadius: radii.md,
    backgroundColor: colors.primarySoft,
    alignItems: "center",
    justifyContent: "center",
  },
  quickLabel: { fontSize: 12, fontWeight: "600", color: colors.text },
  payInfo: { gap: spacing.sm, backgroundColor: colors.infoSoft, borderColor: colors.infoSoft },
  payInfoHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  payInfoTitle: { fontSize: 13, fontWeight: "700", color: colors.info },
  payInfoText: { fontSize: 12, lineHeight: 18, color: colors.info },
  billRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.md,
  },
  billLabel: { fontSize: 12, color: colors.textMuted },
  billValue: { fontSize: 13, fontWeight: "700", color: colors.text },
  muted: { fontSize: 13, color: colors.textMuted },
});
