import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Alert, StyleSheet, Text, View } from "react-native";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { colors, radii, spacing } from "@/lib/theme";

export default function ChangePasswordScreen() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    setError("");
    if (!current || !next || !confirm) {
      setError("Fill in all three fields.");
      return;
    }
    if (next.length < 10) {
      setError("The new password must be at least 10 characters.");
      return;
    }
    if (next !== confirm) {
      setError("The new passwords do not match.");
      return;
    }
    if (next === current) {
      setError("Choose a password different from the current one.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/auth/password/change", {
        current_password: current,
        new_password: next,
      });
      await refreshUser();
      Alert.alert("Password updated", "Use your new password the next time you sign in.", [
        { text: "OK", onPress: () => router.back() },
      ]);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Screen edges={["bottom", "left", "right"]}>
      <Card style={styles.info}>
        <Ionicons name="shield-checkmark-outline" size={20} color={colors.primary} />
        <Text style={styles.infoText}>
          Use at least 10 characters. A mix of letters, numbers and symbols is recommended.
        </Text>
      </Card>

      <Input
        label="Current password"
        value={current}
        onChangeText={setCurrent}
        placeholder="Current password"
        secureTextEntry
        autoCapitalize="none"
        textContentType="password"
      />
      <Input
        label="New password"
        value={next}
        onChangeText={setNext}
        placeholder="At least 10 characters"
        secureTextEntry
        autoCapitalize="none"
        textContentType="newPassword"
      />
      <Input
        label="Confirm new password"
        value={confirm}
        onChangeText={setConfirm}
        placeholder="Repeat the new password"
        secureTextEntry
        autoCapitalize="none"
        textContentType="newPassword"
        onSubmitEditing={submit}
      />

      {error ? (
        <View style={styles.errorBox}>
          <Ionicons name="alert-circle-outline" size={16} color={colors.danger} />
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <Button
        label="Update password"
        icon="checkmark-circle-outline"
        size="lg"
        loading={saving}
        onPress={submit}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  info: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    backgroundColor: colors.primarySoft,
    borderColor: colors.primarySoft,
  },
  infoText: { flex: 1, fontSize: 12, lineHeight: 18, color: colors.primaryDark },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.dangerSoft,
    borderRadius: radii.md,
    padding: spacing.md,
  },
  errorText: { flex: 1, color: colors.danger, fontSize: 13 },
});
