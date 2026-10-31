import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import { Alert, Pressable, StyleSheet, Switch, Text, View } from "react-native";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { ErrorState, Loading } from "@/components/States";
import { api, apiError } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { colors, radii, spacing } from "@/lib/theme";
import type { ReminderSetting } from "@/lib/types";

export default function ReminderSettingsScreen() {
  const { user } = useAuth();
  const settings = useApi<ReminderSetting>("/settings/reminders");
  const [enabled, setEnabled] = useState(true);
  const [preDue, setPreDue] = useState("3");
  const [offsets, setOffsets] = useState("1, 3, 7, 14, 30");
  const [sendHour, setSendHour] = useState("9");
  const [language, setLanguage] = useState<"en" | "sw">("en");
  const [senderId, setSenderId] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!settings.data) return;
    setEnabled(settings.data.enabled);
    setPreDue(String(settings.data.pre_due_days));
    setOffsets(settings.data.escalation_offsets.join(", "));
    setSendHour(String(settings.data.send_hour));
    setLanguage(settings.data.language);
    setSenderId(settings.data.sender_id ?? "");
  }, [settings.data]);

  if (user?.role !== "ADMIN") {
    return (
      <Screen edges={["bottom", "left", "right"]}>
        <ErrorState message="Only administrators can change reminder settings." />
      </Screen>
    );
  }
  if (settings.loading && !settings.data) return <Loading label="Loading reminder settings…" />;
  if (settings.error && !settings.data) {
    return (
      <Screen edges={["bottom", "left", "right"]}>
        <ErrorState message={settings.error} onRetry={settings.reload} />
      </Screen>
    );
  }

  const save = async () => {
    setError("");
    const preDueDays = Number(preDue);
    const hour = Number(sendHour);
    const parsedOffsets = offsets
      .split(",")
      .map((value) => Number(value.trim()))
      .filter((value) => Number.isInteger(value) && value > 0);
    if (!Number.isInteger(preDueDays) || preDueDays < 0) {
      setError("Pre-due days must be zero or a positive whole number.");
      return;
    }
    if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
      setError("Send hour must be between 0 and 23.");
      return;
    }
    if (parsedOffsets.length === 0) {
      setError("Add at least one escalation offset, e.g. 1, 3, 7.");
      return;
    }
    setSaving(true);
    try {
      await api.patch("/settings/reminders", {
        enabled,
        pre_due_days: preDueDays,
        escalation_offsets: parsedOffsets,
        send_hour: hour,
        language,
        sender_id: senderId.trim(),
      });
      await settings.reload();
      Alert.alert("Saved", "Reminder settings have been updated.");
    } catch (err) {
      setError(apiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Screen edges={["bottom", "left", "right"]}>
      <Card style={styles.toggleCard}>
        <View style={styles.toggleText}>
          <Text style={styles.toggleTitle}>Automatic reminders</Text>
          <Text style={styles.toggleHint}>Send SMS reminders for upcoming and overdue rent.</Text>
        </View>
        <Switch
          value={enabled}
          onValueChange={setEnabled}
          trackColor={{ false: colors.border, true: colors.primarySoft }}
          thumbColor={enabled ? colors.primary : colors.surface}
        />
      </Card>

      <Input
        label="Pre-due reminder (days before)"
        value={preDue}
        onChangeText={setPreDue}
        keyboardType="number-pad"
        placeholder="3"
      />
      <Input
        label="Overdue escalation offsets (days)"
        value={offsets}
        onChangeText={setOffsets}
        placeholder="1, 3, 7, 14, 30"
        autoCapitalize="none"
      />
      <Input
        label="Send hour (0–23)"
        value={sendHour}
        onChangeText={setSendHour}
        keyboardType="number-pad"
        placeholder="9"
      />

      <View style={styles.languageBlock}>
        <Text style={styles.label}>Language</Text>
        <View style={styles.languageRow}>
          {(["en", "sw"] as const).map((value) => (
            <Pressable
              key={value}
              onPress={() => setLanguage(value)}
              style={[styles.language, language === value && styles.languageActive]}
            >
              <Text style={[styles.languageText, language === value && styles.languageTextActive]}>
                {value === "en" ? "English" : "Kiswahili"}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      <Input
        label="Sender ID"
        value={senderId}
        onChangeText={setSenderId}
        placeholder="e.g. KWANJU"
        autoCapitalize="characters"
        maxLength={11}
      />

      <Card style={styles.info}>
        <Ionicons name="information-circle-outline" size={18} color={colors.info} />
        <Text style={styles.infoText}>
          Reminder times use the Africa/Nairobi timezone. SMS delivery requires Africa&apos;s Talking
          credentials on the server.
        </Text>
      </Card>

      {error ? (
        <View style={styles.errorBox}>
          <Ionicons name="alert-circle-outline" size={16} color={colors.danger} />
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <Button
        label="Save settings"
        icon="save-outline"
        size="lg"
        loading={saving}
        onPress={save}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  toggleCard: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  toggleText: { flex: 1, gap: 2 },
  toggleTitle: { fontSize: 15, fontWeight: "700", color: colors.text },
  toggleHint: { fontSize: 12, color: colors.textMuted },
  label: { fontSize: 13, fontWeight: "600", color: colors.text },
  languageBlock: { gap: spacing.sm },
  languageRow: { flexDirection: "row", gap: spacing.sm },
  language: {
    flex: 1,
    alignItems: "center",
    paddingVertical: spacing.md,
    borderRadius: radii.md,
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  languageActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  languageText: { fontSize: 13, fontWeight: "600", color: colors.textMuted },
  languageTextActive: { color: colors.white },
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
});
