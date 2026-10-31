import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { Screen } from "@/components/Screen";
import { SectionTitle } from "@/components/SectionTitle";
import { ErrorState, Loading } from "@/components/States";
import { useApi } from "@/lib/useApi";
import { formatKES, monthLabel } from "@/lib/format";
import { colors, radii, spacing } from "@/lib/theme";
import type { ArrearsAgeing, ExpectedVsCollected, OccupancyRow } from "@/lib/types";

const bucketLabels: Record<string, string> = {
  current: "Current",
  "1-7": "1–7 days",
  "8-30": "8–30 days",
  "31+": "31+ days",
};

export default function ReportsScreen() {
  const collections = useApi<ExpectedVsCollected[]>("/reports/expected-vs-collected", {
    months: 6,
  });
  const occupancy = useApi<OccupancyRow[]>("/reports/occupancy");
  const ageing = useApi<ArrearsAgeing>("/reports/arrears-ageing");

  const loading =
    (collections.loading && !collections.data) ||
    (occupancy.loading && !occupancy.data) ||
    (ageing.loading && !ageing.data);
  const error = collections.error || occupancy.error || ageing.error;

  if (loading) return <Loading label="Building reports…" />;
  if (error && !collections.data && !occupancy.data && !ageing.data) {
    return (
      <Screen>
        <ErrorState
          message={error}
          onRetry={() => {
            collections.reload();
            occupancy.reload();
            ageing.reload();
          }}
        />
      </Screen>
    );
  }

  const rows = collections.data ?? [];
  const latest = rows[rows.length - 1];
  const totalExpected = rows.reduce((sum, row) => sum + Number(row.expected), 0);
  const totalCollected = rows.reduce((sum, row) => sum + Number(row.collected), 0);
  const overallRate = totalExpected > 0 ? Math.round((totalCollected / totalExpected) * 100) : 0;

  return (
    <Screen
      refreshing={collections.loading || occupancy.loading || ageing.loading}
      onRefresh={() => {
        collections.reload();
        occupancy.reload();
        ageing.reload();
      }}
    >
      <Text style={styles.title}>Reports</Text>

      <Card style={styles.hero}>
        <View>
          <Text style={styles.heroLabel}>Collection rate · last 6 months</Text>
          <Text style={styles.heroValue}>{overallRate}%</Text>
          <Text style={styles.heroHint}>
            {formatKES(totalCollected)} of {formatKES(totalExpected)}
          </Text>
        </View>
        <Ionicons name="stats-chart" size={40} color="#5EEAD4" />
      </Card>

      {latest ? (
        <View style={styles.grid}>
          <MiniStat label={monthLabel(latest.month)} value={`${latest.rate}%`} hint="Latest month" />
          <MiniStat
            label="Difference"
            value={formatKES(latest.difference)}
            hint="Collected vs expected"
          />
        </View>
      ) : null}

      <SectionTitle title="Expected vs collected" />
      {rows.length === 0 ? (
        <Text style={styles.muted}>No collection history yet.</Text>
      ) : (
        <Card style={styles.list}>
          {rows
            .slice()
            .reverse()
            .map((row, index) => (
              <View key={row.month} style={[styles.row, index > 0 && styles.rowBorder]}>
                <View style={styles.rowLeft}>
                  <Text style={styles.rowTitle}>{monthLabel(row.month)}</Text>
                  <Text style={styles.rowMeta}>
                    {formatKES(row.collected)} of {formatKES(row.expected)}
                  </Text>
                </View>
                <View style={styles.rowRight}>
                  <Text style={styles.rate}>{row.rate}%</Text>
                  <View style={styles.miniTrack}>
                    <View
                      style={[
                        styles.miniFill,
                        { width: `${Math.min(100, Math.max(0, row.rate))}%` },
                      ]}
                    />
                  </View>
                </View>
              </View>
            ))}
        </Card>
      )}

      <SectionTitle title="Occupancy" />
      {(occupancy.data ?? []).map((row) => (
        <Card key={row.property_id} style={styles.occupancy}>
          <View style={styles.rowLeft}>
            <Text style={styles.rowTitle}>{row.property}</Text>
            <Text style={styles.rowMeta}>
              {row.occupied} occupied · {row.vacant} vacant · {row.maintenance} maintenance
            </Text>
          </View>
          <View style={styles.occupancyRate}>
            <Text style={styles.rate}>{row.occupancy_rate}%</Text>
            <Text style={styles.rowMeta}>{row.units} units</Text>
          </View>
        </Card>
      ))}

      <SectionTitle title="Arrears ageing" />
      <View style={styles.grid}>
        {Object.entries(bucketLabels).map(([key, label]) => (
          <MiniStat
            key={key}
            label={label}
            value={formatKES(ageing.data?.totals[key] ?? 0)}
            hint="Outstanding"
            tone={key === "31+" ? "danger" : key === "current" ? "success" : "warning"}
          />
        ))}
      </View>
      <Card style={styles.total}>
        <Text style={styles.totalLabel}>Total outstanding</Text>
        <Text style={styles.totalValue}>{formatKES(ageing.data?.total_outstanding ?? 0)}</Text>
      </Card>
    </Screen>
  );
}

function MiniStat({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "success" | "warning" | "danger";
}) {
  const toneColor = {
    neutral: colors.text,
    success: colors.success,
    warning: colors.warning,
    danger: colors.danger,
  }[tone];
  return (
    <Card style={styles.mini}>
      <Text style={styles.miniLabel}>{label}</Text>
      <Text style={[styles.miniValue, { color: toneColor }]} numberOfLines={1} adjustsFontSizeToFit>
        {value}
      </Text>
      {hint ? <Text style={styles.rowMeta}>{hint}</Text> : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 26, fontWeight: "800", color: colors.text },
  hero: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.primaryDark,
  },
  heroLabel: { fontSize: 12, color: "#C7E7E3", fontWeight: "600" },
  heroValue: { fontSize: 30, fontWeight: "800", color: colors.white, marginTop: 4 },
  heroHint: { fontSize: 12, color: "#C7E7E3" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.md },
  mini: { flex: 1, minWidth: "45%", gap: 4 },
  miniLabel: { fontSize: 12, color: colors.textMuted, fontWeight: "600" },
  miniValue: { fontSize: 19, fontWeight: "800" },
  list: { padding: 0, overflow: "hidden" },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  rowBorder: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border },
  rowLeft: { flex: 1, gap: 2 },
  rowRight: { alignItems: "flex-end", gap: 4, minWidth: 70 },
  rowTitle: { fontSize: 14, fontWeight: "700", color: colors.text },
  rowMeta: { fontSize: 11, color: colors.textMuted },
  rate: { fontSize: 14, fontWeight: "700", color: colors.text },
  miniTrack: {
    width: 70,
    height: 5,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
    overflow: "hidden",
  },
  miniFill: { height: 5, borderRadius: radii.pill, backgroundColor: colors.primary },
  occupancy: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  occupancyRate: { alignItems: "flex-end", gap: 2 },
  muted: { fontSize: 13, color: colors.textMuted },
  total: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.primarySoft,
  },
  totalLabel: { fontSize: 13, fontWeight: "700", color: colors.primaryDark },
  totalValue: { fontSize: 18, fontWeight: "800", color: colors.primaryDark },
});
