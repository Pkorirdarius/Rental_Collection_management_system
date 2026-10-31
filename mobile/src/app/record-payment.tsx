import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useMemo, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { EmptyState, ErrorState, Loading } from "@/components/States";
import { api, apiError } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { formatKES, statusTone } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { Lease, Paginated, Payment } from "@/lib/types";

interface ReceiptResult {
  receiptNumber: string;
  amount: string;
  tenantName: string;
  tenantId: string;
}

export default function RecordPaymentScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ tenantId?: string; leaseId?: string }>();
  const leases = useApi<Paginated<Lease>>("/leases/", { page_size: 100 });
  const [selected, setSelected] = useState<Lease | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ReceiptResult | null>(null);

  const activeLeases = useMemo(
    () => (leases.data?.results ?? []).filter((lease) => lease.status === "ACTIVE"),
    [leases.data],
  );

  useEffect(() => {
    if (selected || activeLeases.length === 0) return;
    const byId = params.leaseId ? activeLeases.find((lease) => lease.id === params.leaseId) : null;
    const byTenant = params.tenantId
      ? activeLeases.find((lease) => lease.tenant === params.tenantId)
      : null;
    const only = activeLeases.length === 1 ? activeLeases[0] : null;
    const chosen = byId ?? byTenant ?? only;
    if (chosen) {
      setSelected(chosen);
      setAmount(Number(chosen.balance) > 0 ? chosen.balance : chosen.rent_amount);
    }
  }, [activeLeases, params.leaseId, params.tenantId, selected]);

  const visibleLeases = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return activeLeases;
    return activeLeases.filter(
      (lease) =>
        lease.tenant_name.toLowerCase().includes(term) ||
        lease.unit_code.toLowerCase().includes(term) ||
        lease.property_name.toLowerCase().includes(term),
    );
  }, [activeLeases, search]);

  const pickLease = (lease: Lease) => {
    setSelected(lease);
    setAmount(Number(lease.balance) > 0 ? lease.balance : lease.rent_amount);
    setPickerOpen(false);
    setSearch("");
    setError("");
  };

  const reset = () => {
    setResult(null);
    setSelected(null);
    setAmount("");
    setNote("");
    setError("");
  };

  const submit = async () => {
    setError("");
    if (!selected) {
      setError("Select the tenant and lease first.");
      return;
    }
    const value = Number(amount.replace(/,/g, ""));
    if (!value || value <= 0) {
      setError("Enter an amount greater than zero.");
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post<Payment>("/payments/cash", {
        tenant: selected.tenant,
        lease: selected.id,
        amount: value,
        note: note.trim(),
        idempotency_key: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
      });
      setResult({
        receiptNumber: data.receipt_number,
        amount: data.amount,
        tenantName: selected.tenant_name,
        tenantId: selected.tenant,
      });
    } catch (err) {
      setError(apiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (leases.loading && !leases.data) return <Loading label="Loading leases…" />;
  if (leases.error && !leases.data) {
    return (
      <Screen edges={["bottom", "left", "right"]}>
        <ErrorState message={leases.error} onRetry={leases.reload} />
      </Screen>
    );
  }

  if (result) {
    return (
      <Screen edges={["bottom", "left", "right"]}>
        <View style={styles.success}>
          <View style={styles.successIcon}>
            <Ionicons name="checkmark" size={38} color={colors.white} />
          </View>
          <Text style={styles.successTitle}>Payment recorded</Text>
          <Text style={styles.successAmount}>{formatKES(result.amount)}</Text>
          <Text style={styles.successText}>
            {result.tenantName} · Receipt {result.receiptNumber || "pending"}
          </Text>
          <View style={styles.successActions}>
            <Button
              label="View tenant"
              icon="person-outline"
              onPress={() => router.replace(`/tenant/${result.tenantId}`)}
            />
            <Button label="Record another" variant="secondary" onPress={reset} />
            <Button label="Done" variant="ghost" onPress={() => router.back()} />
          </View>
        </View>
      </Screen>
    );
  }

  if (activeLeases.length === 0) {
    return (
      <Screen edges={["bottom", "left", "right"]}>
        <EmptyState
          title="No active leases"
          message="Activate a lease before recording payments."
          icon="document-text-outline"
        />
      </Screen>
    );
  }

  return (
    <Screen edges={["bottom", "left", "right"]}>
      <Text style={styles.intro}>
        Record a cash payment. A numbered receipt is issued and sent to the tenant by SMS.
      </Text>

      <View style={styles.labelRow}>
        <Text style={styles.label}>Tenant and lease</Text>
      </View>
      <Pressable onPress={() => setPickerOpen(true)}>
        <Card style={styles.selectedCard}>
          {selected ? (
            <>
              <Avatar name={selected.tenant_name} />
              <View style={styles.selectedBody}>
                <Text style={styles.selectedName}>{selected.tenant_name}</Text>
                <Text style={styles.selectedMeta}>
                  {selected.property_name} · {selected.unit_code}
                </Text>
                <View style={styles.selectedBottom}>
                  <Badge label={selected.payment_status} tone={statusTone(selected.payment_status)} />
                  <Text style={styles.selectedBalance}>
                    Balance {formatKES(selected.balance)}
                  </Text>
                </View>
              </View>
            </>
          ) : (
            <View style={styles.placeholder}>
              <Ionicons name="person-add-outline" size={22} color={colors.primary} />
              <Text style={styles.placeholderText}>Choose a tenant</Text>
            </View>
          )}
          <Ionicons name="chevron-down" size={18} color={colors.textMuted} />
        </Card>
      </Pressable>

      <View>
        <Text style={styles.label}>Amount</Text>
        <View style={styles.amountRow}>
          <Text style={styles.currency}>KES</Text>
          <TextInput
            value={amount}
            onChangeText={setAmount}
            placeholder="0"
            placeholderTextColor={colors.textMuted}
            keyboardType="decimal-pad"
            style={styles.amountInput}
          />
        </View>
        {selected ? (
          <View style={styles.quickRow}>
            {Number(selected.balance) > 0 ? (
              <QuickAmount
                label={`Balance ${formatKES(selected.balance)}`}
                onPress={() => setAmount(selected.balance)}
              />
            ) : null}
            <QuickAmount
              label={`Rent ${formatKES(selected.rent_amount)}`}
              onPress={() => setAmount(selected.rent_amount)}
            />
          </View>
        ) : null}
      </View>

      <Input
        label="Note (optional)"
        value={note}
        onChangeText={setNote}
        placeholder="e.g. October rent, paid at the office"
        multiline
        numberOfLines={3}
        style={styles.note}
      />

      <Card style={styles.info}>
        <Ionicons name="information-circle-outline" size={18} color={colors.info} />
        <Text style={styles.infoText}>
          M-Pesa payments are matched automatically. Only use this form for cash or bank payments
          handed to you.
        </Text>
      </Card>

      {error ? (
        <View style={styles.errorBox}>
          <Ionicons name="alert-circle-outline" size={16} color={colors.danger} />
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <Button
        label="Record payment"
        icon="checkmark-circle-outline"
        size="lg"
        loading={submitting}
        onPress={submit}
      />

      <Modal
        visible={pickerOpen}
        animationType="slide"
        transparent
        onRequestClose={() => setPickerOpen(false)}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select tenant</Text>
              <Pressable onPress={() => setPickerOpen(false)} hitSlop={10}>
                <Ionicons name="close" size={24} color={colors.text} />
              </Pressable>
            </View>
            <View style={styles.search}>
              <Ionicons name="search" size={18} color={colors.textMuted} />
              <TextInput
                value={search}
                onChangeText={setSearch}
                placeholder="Search tenant, unit or property"
                placeholderTextColor={colors.textMuted}
                style={styles.searchInput}
                autoCapitalize="none"
              />
            </View>
            <ScrollView keyboardShouldPersistTaps="handled">
              {visibleLeases.map((lease) => (
                <Pressable
                  key={lease.id}
                  onPress={() => pickLease(lease)}
                  style={({ pressed }) => [styles.pickerRow, pressed && styles.pickerPressed]}
                >
                  <Avatar name={lease.tenant_name} size={38} />
                  <View style={styles.pickerBody}>
                    <Text style={styles.pickerName}>{lease.tenant_name}</Text>
                    <Text style={styles.pickerMeta}>
                      {lease.property_name} · {lease.unit_code} · {formatKES(lease.balance)}
                    </Text>
                  </View>
                  <Badge label={lease.payment_status} tone={statusTone(lease.payment_status)} />
                </Pressable>
              ))}
              {visibleLeases.length === 0 ? (
                <Text style={styles.noResults}>No matching active leases.</Text>
              ) : null}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

function QuickAmount({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={styles.quick}>
      <Text style={styles.quickText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  intro: { fontSize: 13, color: colors.textMuted, lineHeight: 19 },
  labelRow: { flexDirection: "row", justifyContent: "space-between" },
  label: { fontSize: 13, fontWeight: "600", color: colors.text },
  selectedCard: { flexDirection: "row", alignItems: "center", gap: spacing.md, marginTop: spacing.sm },
  selectedBody: { flex: 1, gap: 3 },
  selectedName: { fontSize: 15, fontWeight: "700", color: colors.text },
  selectedMeta: { fontSize: 12, color: colors.textMuted },
  selectedBottom: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: 4 },
  selectedBalance: { fontSize: 11, color: colors.textMuted },
  placeholder: { flex: 1, flexDirection: "row", alignItems: "center", gap: spacing.sm },
  placeholderText: { fontSize: 14, fontWeight: "600", color: colors.primary },
  amountRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    marginTop: spacing.sm,
  },
  currency: { fontSize: 15, fontWeight: "700", color: colors.textMuted },
  amountInput: { flex: 1, paddingVertical: 15, fontSize: 24, fontWeight: "700", color: colors.text },
  quickRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm },
  quick: {
    backgroundColor: colors.primarySoft,
    borderRadius: radii.pill,
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
  },
  quickText: { fontSize: 12, fontWeight: "600", color: colors.primaryDark },
  note: { minHeight: 78, textAlignVertical: "top" },
  info: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    backgroundColor: colors.infoSoft,
    borderColor: colors.infoSoft,
  },
  infoText: { flex: 1, fontSize: 12, lineHeight: 17, color: colors.info },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.dangerSoft,
    borderRadius: radii.md,
    padding: spacing.md,
  },
  errorText: { flex: 1, color: colors.danger, fontSize: 13 },
  success: { alignItems: "center", gap: spacing.sm, paddingTop: spacing.xxl },
  successIcon: {
    width: 78,
    height: 78,
    borderRadius: radii.pill,
    backgroundColor: colors.success,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.sm,
  },
  successTitle: { fontSize: 22, fontWeight: "800", color: colors.text },
  successAmount: { fontSize: 30, fontWeight: "800", color: colors.primary },
  successText: { fontSize: 13, color: colors.textMuted, textAlign: "center" },
  successActions: { alignSelf: "stretch", gap: spacing.sm, marginTop: spacing.lg },
  modalBackdrop: { flex: 1, backgroundColor: "rgba(15,23,42,0.45)", justifyContent: "flex-end" },
  modalSheet: {
    maxHeight: "82%",
    backgroundColor: colors.background,
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    padding: spacing.lg,
    paddingBottom: spacing.xxl,
    gap: spacing.md,
  },
  modalHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  modalTitle: { fontSize: 19, fontWeight: "800", color: colors.text },
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
  searchInput: { flex: 1, paddingVertical: 11, fontSize: 14, color: colors.text },
  pickerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  pickerPressed: { backgroundColor: colors.surfaceMuted },
  pickerBody: { flex: 1, gap: 2 },
  pickerName: { fontSize: 14, fontWeight: "700", color: colors.text },
  pickerMeta: { fontSize: 11, color: colors.textMuted },
  noResults: { textAlign: "center", color: colors.textMuted, fontSize: 13, padding: spacing.xl },
});
