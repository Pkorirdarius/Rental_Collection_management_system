import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { initials } from "@/lib/format";
import { colors, radii } from "@/lib/theme";

export function Avatar({ name, size = 42 }: { name: string; size?: number }) {
  return (
    <View
      style={[
        styles.avatar,
        { width: size, height: size, borderRadius: size / 2 },
      ]}
    >
      <Text style={[styles.text, { fontSize: size * 0.36 }]}>{initials(name)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  avatar: {
    backgroundColor: colors.primarySoft,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.pill,
  },
  text: { color: colors.primaryDark, fontWeight: "700" },
});
