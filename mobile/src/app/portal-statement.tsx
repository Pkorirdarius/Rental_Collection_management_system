import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Alert, StyleSheet, Text, View } from "react-native";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Screen } from "@/components/Screen";
import { SectionTitle } from "@/components/SectionTitle";
import { ErrorState, Loading } from "@/components/States";
import { openAuthenticatedPdf } from "@/lib/download";
import { useApi } from "@/lib/useApi";
import { formatDate, formatKES, statusTone } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { LeaseStatement, StatementEntry, TenantStatement } from "@/lib/types";

export default function PortalStatementScreen() {
  const statement = useApi<TenantStatement>("/portal/me/statement");
  const [downloading, setDownloading] = useState(false);

  const download = async () => {
    setDownloading(true);
    try {
      await openAuthenticatedPdf("/portal/me/statement/?format=pdf", "my-statement.pdf");
    } catch (err) {
      Alert.alert("Could not open statement", err instanceof Error ? err.message : "Try again.");
    } finally {
      setDownloading(false);
    }
  };

  if (statement.loading && !statement.data) return <Loading label="Building statement…" />;
  if (statement.error && !statement.data) {
    return (
      <Screen edges={["bottom", "left", "right"]}>
        <ErrorState message={statement.error} onRetry={statement.reload} />
      </Screen>
    );
  }
  const data = statement.data;
  if (!data) return null;

  return (
    <Screen edges={["bottom", "left", "right"]}>
      <Card style={styles.summary}>
        <View>
          <Text style={styles.summaryLabel}>Total outstanding</Text>
          <Text style={styles.summaryValue}>{formatKES(data.total_balance)}</Text>
          <Text style={styles.summaryHint}>{data.tenant}</Text>
        </View>
        <Ionicons name="document-text" size={38} color="#5EEAD4" />
      </Card>

      <Button
        label="Download PDF"
        icon="download-outline"
        variant="secondary"
        loading={downloading}
        onPress={download}
      />

      {data.leases.length === 0 ? (
        <Card>
          <Text style={styles.muted}>No lease history yet.</Text>
        </Card>
      ) : (
        data.leases.map((lease) => <LeaseSection key={lease.lease_id} lease={lease} />)
      )}
    </Screen>
  );
}

function LeaseSection({ lease }: { lease: LeaseStatement }) {
  return (
    <View style={styles.section}>
      <SectionTitle
        title={`${lease.property} · ${lease.unit}`}
        action={<Badge label={lease.status} tone={statusTone(lease.status)} />}
      />
      <Card style={styles.leaseCard}>
        <View style={styles.leaseTop}>
          <View>
            <Text style={styles.leaseMeta}>Balance</Text>
            <Text style={styles.leaseBalance}>{formatKES(lease.balance)}</Text>
          </View>
          {lease.days_overdue > 0 ? (
            <View style={styles.lateBox}>
              <Ionicons name="time-outline" size={14} color={colors.danger} />
              <Text style={styles.lateText}>{lease.days_overdue} days late</Text>
            </View>
          ) : null}
        </View>

        {lease.entries.length === 0 ? (
          <Text style={styles.muted}>No ledger entries.</Text>
        ) : (
          lease.entries.map((entry, index) => (
            <EntryRow key={entry.id} entry={entry} last={index === lease.entries.length - 1} />
          ))
        )}
      </Card>
    </View>
  );
}

function EntryRow({ entry, last }: { entry: StatementEntry; last: boolean }) {
  const debit = Number(entry.debit);
  const credit = Number(entry.credit);
  return (
    <View style={[styles.entry, !last && styles.entryBorder]}>
      <View style={styles.entryTop}>
        <Text style={styles.entryDescription} numberOfLines={2}>
          {entry.description}
        </Text>
        <Text style={[styles.entryAmount, credit > 0 && styles.credit]}>
          {credit > 0 ? `− ${formatKES(credit)}` : formatKES(debit)}
        </Text>
      </View>
      <View style={styles.entryBottom}>
        <Text style={styles.entryMeta}>
          {formatDate(entry.date)}
          {entry.reference ? ` · ${entry.reference}` : ""}
        </Text>
        <Text style={styles.entryBalance}>Bal {formatKES(entry.balance)}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  summary: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.primaryDark,
  },
  summaryLabel: { fontSize: 12, color: "#C7E7E3", fontWeight: "600" },
  summaryValue: { fontSize: 28, fontWeight: "800", color: colors.white, marginTop: 4 },
  summaryHint: { fontSize: 12, color: "#C7E7E3" },
  section: { gap: spacing.sm },
  leaseCard: { gap: spacing.md },
  leaseTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  leaseMeta: { fontSize: 11, color: colors.textMuted },
  leaseBalance: { fontSize: 20, fontWeight: "800", color: colors.text },
  lateBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.dangerSoft,
    borderRadius: radii.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
  },
  lateText: { fontSize: 11, fontWeight: "600", color: colors.danger },
  entry: { gap: 4, paddingVertical: spacing.sm },
  entryBorder: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  entryTop: { flexDirection: "row", alignItems: "flex-start", gap: spacing.md },
  entryDescription: { flex: 1, fontSize: 13, fontWeight: "600", color: colors.text },
  entryAmount: { fontSize: 13, fontWeight: "700", color: colors.text },
  credit: { color: colors.success },
  entryBottom: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.sm },
  entryMeta: { flex: 1, fontSize: 11, color: colors.textMuted },
  entryBalance: { fontSize: 11, color: colors.textMuted },
  muted: { fontSize: 13, color: colors.textMuted },
});
