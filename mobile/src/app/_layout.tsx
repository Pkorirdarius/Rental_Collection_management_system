import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import React from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider } from "@/lib/auth";
import { colors } from "@/lib/theme";

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AuthProvider>
          <StatusBar style="dark" />
          <Stack
            screenOptions={{
              headerShown: false,
              contentStyle: { backgroundColor: colors.background },
              headerStyle: { backgroundColor: colors.surface },
              headerTintColor: colors.text,
              headerTitleStyle: { fontWeight: "700" },
            }}
          >
            <Stack.Screen name="login" options={{ animation: "fade" }} />
            <Stack.Screen name="(admin)" />
            <Stack.Screen name="(portal)" />
            <Stack.Screen
              name="tenant/[id]"
              options={{ headerShown: true, title: "Tenant", headerBackTitle: "Back" }}
            />
            <Stack.Screen
              name="record-payment"
              options={{ headerShown: true, title: "Record payment", presentation: "modal" }}
            />
            <Stack.Screen
              name="change-password"
              options={{ headerShown: true, title: "Change password", presentation: "modal" }}
            />
            <Stack.Screen
              name="statement"
              options={{ headerShown: true, title: "Statement" }}
            />
            <Stack.Screen
              name="reminder-settings"
              options={{ headerShown: true, title: "Reminder settings" }}
            />
            <Stack.Screen
              name="portal-pay"
              options={{ headerShown: true, title: "Pay with M-Pesa" }}
            />
            <Stack.Screen
              name="portal-statement"
              options={{ headerShown: true, title: "My statement" }}
            />
          </Stack>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
