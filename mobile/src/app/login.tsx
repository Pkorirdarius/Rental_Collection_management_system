import { Ionicons } from "@expo/vector-icons";
import { Redirect, useRouter } from "expo-router";
import React, { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { colors, radii, spacing } from "@/lib/theme";

export default function LoginScreen() {
  const { user, login, verify2fa } = useAuth();
  const router = useRouter();
  const [identifier, setIdentifier] = useState("admin@demo.rent");
  const [password, setPassword] = useState("Demo12345!");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (user) {
    return <Redirect href={user.role === "TENANT" ? "/(portal)" : "/(admin)"} />;
  }

  const submit = async () => {
    setError("");
    if (!identifier.trim() || !password) {
      setError("Enter your email or phone and password.");
      return;
    }
    setLoading(true);
    try {
      if (challenge) {
        if (!code.trim()) throw new Error("Enter your 6-digit authenticator code.");
        const role = await verify2fa(challenge, code.trim());
        router.replace(role === "TENANT" ? "/(portal)" : "/(admin)");
        return;
      }
      const outcome = await login(identifier.trim(), password);
      if (outcome.mfaRequired && outcome.challenge) {
        setChallenge(outcome.challenge);
        setCode("");
        return;
      }
      router.replace(outcome.role === "TENANT" ? "/(portal)" : "/(admin)");
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.brand}>
            <View style={styles.logo}>
              <Ionicons name="business" size={30} color={colors.white} />
            </View>
            <Text style={styles.title}>Rent Manager</Text>
            <Text style={styles.subtitle}>Collections, tenants and M-Pesa in one place.</Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>{challenge ? "Two-factor check" : "Welcome back"}</Text>
            <Text style={styles.cardSubtitle}>
              {challenge
                ? "Enter the code from your authenticator app."
                : "Sign in with your email address or phone number."}
            </Text>

            {challenge ? (
              <Input
                label="Authenticator code"
                value={code}
                onChangeText={setCode}
                placeholder="123456"
                keyboardType="number-pad"
                maxLength={6}
                autoFocus
                onSubmitEditing={submit}
              />
            ) : (
              <>
                <Input
                  label="Email or phone"
                  value={identifier}
                  onChangeText={setIdentifier}
                  placeholder="admin@demo.rent"
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="email-address"
                  textContentType="username"
                  returnKeyType="next"
                />
                <View>
                  <Input
                    label="Password"
                    value={password}
                    onChangeText={setPassword}
                    placeholder="Your password"
                    secureTextEntry={!showPassword}
                    autoCapitalize="none"
                    textContentType="password"
                    returnKeyType="go"
                    onSubmitEditing={submit}
                    style={styles.passwordInput}
                  />
                  <Pressable
                    style={styles.eye}
                    onPress={() => setShowPassword((value) => !value)}
                    hitSlop={10}
                  >
                    <Ionicons
                      name={showPassword ? "eye-off-outline" : "eye-outline"}
                      size={20}
                      color={colors.textMuted}
                    />
                  </Pressable>
                </View>
              </>
            )}

            {error ? (
              <View style={styles.errorBox}>
                <Ionicons name="alert-circle-outline" size={16} color={colors.danger} />
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            <Button
              label={challenge ? "Verify code" : "Sign in"}
              onPress={submit}
              loading={loading}
              size="lg"
              icon={challenge ? "shield-checkmark-outline" : "log-in-outline"}
            />

            {challenge ? (
              <Button
                label="Use a different account"
                onPress={() => {
                  setChallenge(null);
                  setCode("");
                  setError("");
                }}
                variant="ghost"
              />
            ) : null}
          </View>

          <View style={styles.demo}>
            <Ionicons name="information-circle-outline" size={16} color={colors.textMuted} />
            <Text style={styles.demoText}>
              Demo: admin@demo.rent · Demo12345!{"\n"}
              Tenant: grace@demo.rent · Demo12345!
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  flex: { flex: 1 },
  content: { padding: spacing.xl, gap: spacing.xl, paddingBottom: spacing.xxl },
  brand: { alignItems: "center", gap: spacing.sm, paddingTop: spacing.xxl },
  logo: {
    width: 64,
    height: 64,
    borderRadius: radii.xl,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.sm,
  },
  title: { fontSize: 28, fontWeight: "800", color: colors.text },
  subtitle: { fontSize: 14, color: colors.textMuted, textAlign: "center" },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  cardTitle: { fontSize: 21, fontWeight: "700", color: colors.text },
  cardSubtitle: { fontSize: 13, color: colors.textMuted, marginTop: -8 },
  passwordInput: { paddingRight: 48 },
  eye: { position: "absolute", right: 14, bottom: 14 },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.dangerSoft,
    borderRadius: radii.md,
    padding: spacing.md,
  },
  errorText: { flex: 1, color: colors.danger, fontSize: 13 },
  demo: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    paddingHorizontal: spacing.sm,
  },
  demoText: { flex: 1, fontSize: 12, lineHeight: 18, color: colors.textMuted },
});
