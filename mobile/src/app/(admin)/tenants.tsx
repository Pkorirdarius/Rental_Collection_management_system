import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { Screen } from "@/components/Screen";
import { ErrorState, Loading } from "@/components/States";
import { TenantRow } from "@/components/TenantRow";
import { useApi } from "@/lib/useApi";
import { formatKES, formatNumber } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { Paginated, Tenant } from "@/lib/types";

type Filter = "ALL" | "OVERDUE" | "PAID";

const filters: { key: Filter; label: string }[] = [
  { key: "ALL", label: "All" },
  { key: "OVERDUE", label: "Overdue" },
  { key: "PAID", label: "Paid" },
];

export default function TenantsScreen() {
  const router = useRouter();
  const { data, loading, error, reload } = useApi<Paginated<Tenant>>("/tenants/", {
    page_size: 100,
  });
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("ALL");

  const tenants = useMemo(() => data?.results ?? [], [data]);
  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return tenants.filter((tenant) => {
      const matchesSearch =
        !term ||
        tenant.full_name.toLowerCase().includes(term) ||
        tenant.phone.toLowerCase().includes(term) ||
        (tenant.unit?.code ?? "").toLowerCase().includes(term) ||
        (tenant.unit?.property ?? "").toLowerCase().includes(term);
      const status = (tenant.lease_status ?? "").toUpperCase();
      const matchesFilter =
        filter === "ALL" ||
        (filter === "OVERDUE" && status === "OVERDUE") ||
        (filter === "PAID" && status === "PAID");
      return matchesSearch && matchesFilter;
    });
  }, [tenants, search, filter]);

  const outstanding = tenants.reduce((sum, tenant) => sum + Number(tenant.balance ?? 0), 0);

  if (loading && !data) return <Loading label="Loading tenants…" />;
  if (error && !data) {
    return (
      <Screen>
        <ErrorState message={error} onRetry={reload} />
      </Screen>
    );
  }

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <View style={styles.heading}>
        <View>
          <Text style={styles.title}>Tenants</Text>
          <Text style={styles.subtitle}>
            {formatNumber(tenants.length)} tenants · {formatKES(outstanding)} outstanding
          </Text>
        </View>
        <View style={styles.countBadge}>
          <Ionicons name="people" size={18} color={colors.primary} />
        </View>
      </View>

      <View style={styles.search}>
        <Ionicons name="search" size={18} color={colors.textMuted} />
        <TextInput
          value={search}
          onChangeText={setSearch}
          placeholder="Search name, phone or unit"
          placeholderTextColor={colors.textMuted}
          style={styles.searchInput}
          autoCapitalize="none"
          returnKeyType="search"
        />
        {search ? (
          <Pressable onPress={() => setSearch("")} hitSlop={8}>
            <Ionicons name="close-circle" size={18} color={colors.textMuted} />
          </Pressable>
        ) : null}
      </View>

      <View style={styles.filters}>
        {filters.map((item) => {
          const active = filter === item.key;
          return (
            <Pressable
              key={item.key}
              onPress={() => setFilter(item.key)}
              style={[styles.filter, active && styles.filterActive]}
            >
              <Text style={[styles.filterText, active && styles.filterTextActive]}>
                {item.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {visible.length === 0 ? (
        <View style={styles.empty}>
          <Ionicons name="search-outline" size={36} color={colors.textMuted} />
          <Text style={styles.emptyTitle}>No tenants found</Text>
          <Text style={styles.emptyText}>Try a different search or filter.</Text>
        </View>
      ) : (
        visible.map((tenant) => (
          <TenantRow
            key={tenant.id}
            tenant={tenant}
            onPress={() => router.push(`/tenant/${tenant.id}`)}
          />
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  heading: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  title: { fontSize: 26, fontWeight: "800", color: colors.text },
  subtitle: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  countBadge: {
    width: 42,
    height: 42,
    borderRadius: radii.md,
    backgroundColor: colors.primarySoft,
    alignItems: "center",
    justifyContent: "center",
  },
  search: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
  },
  searchInput: { flex: 1, paddingVertical: 12, fontSize: 14, color: colors.text },
  filters: { flexDirection: "row", gap: spacing.sm },
  filter: {
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
  },
  filterActive: { backgroundColor: colors.primary },
  filterText: { fontSize: 12, fontWeight: "600", color: colors.textMuted },
  filterTextActive: { color: colors.white },
  empty: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.xxl },
  emptyTitle: { fontSize: 16, fontWeight: "700", color: colors.text },
  emptyText: { fontSize: 13, color: colors.textMuted },
});
