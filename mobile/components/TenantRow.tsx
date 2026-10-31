import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { Avatar } from "./Avatar";
import { Badge } from "./Badge";
import { Card } from "./Card";
import { formatKES, statusTone } from "@/lib/format";
import { colors, spacing } from "@/lib/theme";
import type { Tenant } from "@/lib/types";

export function TenantRow({ tenant, onPress }: { tenant: Tenant; onPress?: () => void }) {
  const tone = statusTone(tenant.lease_status);
  return (
    <Card onPress={onPress} style={styles.card}>
      <Avatar name={tenant.full_name} />
      <View style={styles.body}>
        <View style={styles.top}>
          <Text style={styles.name} numberOfLines={1}>
            {tenant.full_name}
          </Text>
          {tenant.lease_status ? <Badge label={tenant.lease_status} tone={tone} /> : null}
        </View>
        <Text style={styles.meta} numberOfLines={1}>
          {tenant.unit ? `${tenant.unit.property} · ${tenant.unit.code}` : "No active lease"}
        </Text>
        <View style={styles.bottom}>
          <Ionicons name="call-outline" size={13} color={colors.textMuted} />
          <Text style={styles.phone}>{tenant.phone}</Text>
          {tenant.balance !== null ? (
            <Text style={styles.balance}>{formatKES(tenant.balance)}</Text>
          ) : null}
        </View>
      </View>
      <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  body: { flex: 1, gap: 4 },
  top: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  name: { flex: 1, fontSize: 15, fontWeight: "700", color: colors.text },
  meta: { fontSize: 12, color: colors.textMuted },
  bottom: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 2 },
  phone: { fontSize: 12, color: colors.textMuted },
  balance: { marginLeft: "auto", fontSize: 13, fontWeight: "700", color: colors.text },
});
