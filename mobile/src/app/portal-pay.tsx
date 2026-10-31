import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { EmptyState, ErrorState, Loading } from "@/components/States";
import { api, apiError } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { formatKES } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { PortalProfile } from "@/lib/types";

export default function PortalPayScreen() {
  const router = useRouter();
  const profile = useApi<PortalProfile>("/portal/me");
  const [amount, setAmount] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  useEffect(() => {
    if (!profile.data) return;
    setPhone((current) => current || profile.data?.phone || "");
    setAmount((current) => {
      if (current) return current;
      const balance = Number(profile.data?.balance ?? 0);
      return balance > 0 ? profile.data?.balance ?? "" : profile.data?.rent_amount ?? "";
    });
  }, [profile.data]);

  if (profile.loading && !profile.data) return <Loading label="Loading account…" />;
  if (profile.error && !profile.data) {
    return (
      <Screen edges={["bottom", "left", "right"]}>
        <ErrorState message={profile.error} onRetry={profile.reload} />
      </Screen>
    );
  }
  const data = profile.data;
  if (!data) return null;
  if (!data.lease_id) {
    return (
      <Screen edges={["bottom", "left", "right"]}>
        <EmptyState
          title="No active tenancy"
          message="Contact the office to activate your lease before paying."
          icon="home-outline"
        />
      </Screen>
    );
  }

  const submit = async () => {
    setError("");
    const value = Number(amount.replace(/,/g, ""));
    if (!value || value <= 0) {
      setError("Enter an amount greater than zero.");
      return;
    }
    if (!phone.trim()) {
      setError("Enter the M-Pesa phone number.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/portal/me/pay", {
        lease: data.lease_id,
        amount: value,
        phone: phone.trim(),
      });
      setSent(true);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return (
      <Screen edges={["bottom", "left", "right"]}>
        <View style={styles.success}>
          <View style={styles.successIcon}>
            <Ionicons name="phone-portrait-outline" size={38} color={colors.white} />
          </View>
          <Text style={styles.successTitle}>Check your phone</Text>
          <Text style={styles.successText}>
            We sent an M-Pesa request for {formatKES(amount)} to {phone}. Enter your PIN to
            complete the payment.
          </Text>
          <Button
            label="Back to home"
            onPress={() => router.replace("/(portal)")}
            style={styles.successButton}
          />
        </View>
      </Screen>
    );
  }

  return (
    <Screen edges={["bottom", "left", "right"]}>
      <Card style={styles.summary}>
        <View>
          <Text style={styles.summaryLabel}>Current balance</Text>
          <Text style={styles.summaryValue}>{formatKES(data.balance)}</Text>
          <Text style={styles.summaryHint}>
            {data.property} · {data.unit}
          </Text>
        </View>
        <Ionicons name="phone-portrait" size={36} color="#5EEAD4" />
      </Card>

      <Input
        label="Amount (KES)"
        value={amount}
        onChangeText={setAmount}
        placeholder="0"
        keyboardType="decimal-pad"
      />
      <Input
        label="M-Pesa phone"
        value={phone}
        onChangeText={setPhone}
        placeholder="07XX XXX XXX"
        keyboardType="phone-pad"
        autoComplete="tel"
      />

      <Card style={styles.info}>
        <Ionicons name="information-circle-outline" size={18} color={colors.info} />
        <Text style={styles.infoText}>
          You will receive a prompt on your phone. Enter your M-Pesa PIN to complete the payment.
          The receipt appears in your payments tab automatically.
        </Text>
      </Card>

      {error ? (
        <View style={styles.errorBox}>
          <Ionicons name="alert-circle-outline" size={16} color={colors.danger} />
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <Button
        label="Send M-Pesa request"
        icon="send-outline"
        size="lg"
        loading={submitting}
        onPress={submit}
      />
    </Screen>
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
  info: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    backgroundColor: colors.infoSoft,
    borderColor: colors.infoSoft,
  },
  infoText: { flex: 1, fontSize: 12, lineHeight: 18, color: colors.info },
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
  successText: { fontSize: 13, color: colors.textMuted, textAlign: "center", lineHeight: 19 },
  successButton: { alignSelf: "stretch", marginTop: spacing.lg },
});
