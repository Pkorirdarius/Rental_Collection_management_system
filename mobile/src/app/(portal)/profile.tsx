import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { Card } from "@/components/Card";
import { Screen } from "@/components/Screen";
import { ErrorState, Loading } from "@/components/States";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { formatKES, statusTone } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { PortalProfile } from "@/lib/types";

export default function PortalProfileScreen() {
  const profile = useApi<PortalProfile>("/portal/me");
  const { logout } = useAuth();
  const router = useRouter();

  if (profile.loading && !profile.data) return <Loading label="Loading profile…" />;
  if (profile.error && !profile.data) {
    return (
      <Screen>
        <ErrorState message={profile.error} onRetry={profile.reload} />
      </Screen>
    );
  }
  const data = profile.data;
  if (!data) return null;

  const confirmLogout = () => {
    Alert.alert("Sign out?", "You will need to sign in again.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign out",
        style: "destructive",
        onPress: async () => {
          await logout();
          router.replace("/login");
        },
      },
    ]);
  };

  return (
    <Screen refreshing={profile.loading} onRefresh={profile.reload}>
      <Text style={styles.title}>Profile</Text>

      <Card style={styles.profile}>
        <Avatar name={data.full_name} size={58} />
        <View style={styles.profileBody}>
          <Text style={styles.name}>{data.full_name}</Text>
          <Text style={styles.meta}>{data.phone}</Text>
          <Text style={styles.meta}>{data.email}</Text>
          <Badge label={data.status} tone={statusTone(data.status)} />
        </View>
      </Card>

      <Text style={styles.section}>Tenancy</Text>
      <Card style={styles.details}>
        <DetailRow label="Property" value={data.property ?? "—"} />
        <DetailRow label="Unit" value={data.unit ?? "—"} />
        <DetailRow label="Rent" value={formatKES(data.rent_amount)} />
        <DetailRow label="Due day" value={data.due_day ? `Day ${data.due_day}` : "—"} />
        <DetailRow label="Bill reference" value={data.bill_ref ?? "—"} />
        <DetailRow label="Balance" value={formatKES(data.balance)} />
      </Card>

      <Text style={styles.section}>Account</Text>
      <Card style={styles.menu}>
        <MenuRow
          icon="document-text-outline"
          label="My statement"
          onPress={() => router.push("/portal-statement")}
        />
        <Divider />
        <MenuRow
          icon="lock-closed-outline"
          label="Change password"
          onPress={() => router.push("/change-password")}
        />
        <Divider />
        <MenuRow
          icon="log-out-outline"
          label="Sign out"
          danger
          onPress={confirmLogout}
        />
      </Card>

      <Text style={styles.version}>Rent Manager</Text>
    </Screen>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
  );
}

function MenuRow({
  icon,
  label,
  onPress,
  danger = false,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
  danger?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.menuRow, pressed && styles.menuPressed]}
    >
      <View style={[styles.menuIcon, danger && styles.menuIconDanger]}>
        <Ionicons name={icon} size={19} color={danger ? colors.danger : colors.primary} />
      </View>
      <Text style={[styles.menuLabel, danger && { color: colors.danger }]}>{label}</Text>
      <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
    </Pressable>
  );
}

function Divider() {
  return <View style={styles.divider} />;
}

const styles = StyleSheet.create({
  title: { fontSize: 26, fontWeight: "800", color: colors.text },
  profile: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  profileBody: { flex: 1, gap: 3, alignItems: "flex-start" },
  name: { fontSize: 18, fontWeight: "800", color: colors.text },
  meta: { fontSize: 12, color: colors.textMuted },
  section: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textMuted,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginBottom: -spacing.sm,
  },
  details: { gap: spacing.sm },
  detailRow: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md },
  detailLabel: { fontSize: 12, color: colors.textMuted },
  detailValue: { fontSize: 13, fontWeight: "600", color: colors.text },
  menu: { padding: 0, overflow: "hidden" },
  menuRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md + 2,
  },
  menuIcon: {
    width: 38,
    height: 38,
    borderRadius: radii.md,
    backgroundColor: colors.primarySoft,
    alignItems: "center",
    justifyContent: "center",
  },
  menuIconDanger: { backgroundColor: colors.dangerSoft },
  menuLabel: { flex: 1, fontSize: 15, fontWeight: "600", color: colors.text },
  menuPressed: { backgroundColor: colors.surfaceMuted },
  divider: { height: StyleSheet.hairlineWidth, backgroundColor: colors.border, marginLeft: 66 },
  version: { textAlign: "center", fontSize: 11, color: colors.textMuted },
});
