import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import React from "react";
import { StyleSheet } from "react-native";

import { Loading } from "@/components/States";
import { useAuth } from "@/lib/auth";
import { colors } from "@/lib/theme";

export default function AdminLayout() {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Redirect href="/login" />;
  if (user.role === "TENANT") return <Redirect href="/(portal)" />;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: styles.tabBar,
        tabBarLabelStyle: styles.label,
        tabBarItemStyle: styles.item,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarIcon: ({ color, size }) => <Ionicons name="home" size={size} color={typeof color === "string" ? color : colors.textMuted} />,
        }}
      />
      <Tabs.Screen
        name="tenants"
        options={{
          title: "Tenants",
          tabBarIcon: ({ color, size }) => <Ionicons name="people" size={size} color={typeof color === "string" ? color : colors.textMuted} />,
        }}
      />
      <Tabs.Screen
        name="payments"
        options={{
          title: "Payments",
          tabBarIcon: ({ color, size }) => <Ionicons name="wallet" size={size} color={typeof color === "string" ? color : colors.textMuted} />,
        }}
      />
      <Tabs.Screen
        name="more"
        options={{
          title: "More",
          tabBarIcon: ({ color, size }) => <Ionicons name="grid" size={size} color={typeof color === "string" ? color : colors.textMuted} />,
        }}
      />
      <Tabs.Screen name="reports" options={{ href: null }} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: colors.surface,
    borderTopColor: colors.border,
    height: 62,
    paddingTop: 6,
    paddingBottom: 8,
  },
  label: { fontSize: 11, fontWeight: "600" },
  item: { paddingVertical: 2 },
});
