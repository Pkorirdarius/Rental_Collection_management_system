import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import { useRouter } from "expo-router";
import React from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";

import { Avatar } from "@/components/Avatar";
import { Card } from "@/components/Card";
import { Screen } from "@/components/Screen";
import { useAuth } from "@/lib/auth";
import { colors, radii, spacing } from "@/lib/theme";

export default function MoreScreen() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const isAdmin = user?.role === "ADMIN";

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
    <Screen>
      <Text style={styles.title}>More</Text>

      <Card style={styles.profile}>
        <Avatar name={user?.full_name ?? "RM"} size={54} />
        <View style={styles.profileText}>
          <Text style={styles.name}>{user?.full_name}</Text>
          <Text style={styles.role}>{isAdmin ? "Administrator" : "Caretaker"}</Text>
          <Text style={styles.contact}>{user?.email}</Text>
          {user?.phone ? <Text style={styles.contact}>{user.phone}</Text> : null}
        </View>
      </Card>

      <Text style={styles.section}>Manage</Text>
      <Card style={styles.menu}>
        {isAdmin ? (
          <>
            <MenuRow
              icon="bar-chart-outline"
              label="Reports"
              subtitle="Collections, occupancy and arrears ageing"
              onPress={() => router.push("/reports")}
            />
            <Divider />
            <MenuRow
              icon="notifications-outline"
              label="Reminder settings"
              subtitle="SMS cadence, language and sender ID"
              onPress={() => router.push("/reminder-settings")}
            />
            <Divider />
          </>
        ) : null}
        <MenuRow
          icon="lock-closed-outline"
          label="Change password"
          subtitle="Update your sign-in password"
          onPress={() => router.push("/change-password")}
        />
        <Divider />
        <MenuRow
          icon="people-outline"
          label="Tenants"
          subtitle="Browse and search tenant accounts"
          onPress={() => router.push("/tenants")}
        />
      </Card>

      <Text style={styles.section}>Account</Text>
      <Card style={styles.menu}>
        <MenuRow
          icon="log-out-outline"
          label="Sign out"
          subtitle="End this session on this device"
          danger
          onPress={confirmLogout}
        />
      </Card>

      <Text style={styles.version}>
        Rent Manager v{Constants.expoConfig?.version ?? "1.0.0"}
      </Text>
    </Screen>
  );
}

function MenuRow({
  icon,
  label,
  subtitle,
  onPress,
  danger = false,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  subtitle?: string;
  onPress: () => void;
  danger?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
    >
      <View style={[styles.rowIcon, danger && styles.rowIconDanger]}>
        <Ionicons
          name={icon}
          size={19}
          color={danger ? colors.danger : colors.primary}
        />
      </View>
      <View style={styles.rowText}>
        <Text style={[styles.rowLabel, danger && { color: colors.danger }]}>{label}</Text>
        {subtitle ? <Text style={styles.rowSubtitle}>{subtitle}</Text> : null}
      </View>
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
  profileText: { flex: 1, gap: 2 },
  name: { fontSize: 17, fontWeight: "700", color: colors.text },
  role: { fontSize: 12, fontWeight: "600", color: colors.primary },
  contact: { fontSize: 12, color: colors.textMuted },
  section: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textMuted,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginBottom: -spacing.sm,
  },
  menu: { padding: 0, overflow: "hidden" },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md + 2,
  },
  rowPressed: { backgroundColor: colors.surfaceMuted },
  rowIcon: {
    width: 38,
    height: 38,
    borderRadius: radii.md,
    backgroundColor: colors.primarySoft,
    alignItems: "center",
    justifyContent: "center",
  },
  rowIconDanger: { backgroundColor: colors.dangerSoft },
  rowText: { flex: 1, gap: 1 },
  rowLabel: { fontSize: 15, fontWeight: "600", color: colors.text },
  rowSubtitle: { fontSize: 11, color: colors.textMuted },
  divider: { height: StyleSheet.hairlineWidth, backgroundColor: colors.border, marginLeft: 66 },
  version: { textAlign: "center", fontSize: 11, color: colors.textMuted },
});
