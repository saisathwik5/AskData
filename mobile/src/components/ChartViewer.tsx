import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { ChartSpec } from "../types";

interface Props {
  spec: ChartSpec;
}

const BAR_COLORS = ["#2563eb", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4"];

export default function ChartViewer({ spec }: Props) {
  if (!spec || !spec.data || spec.data.length === 0) return null;

  const xKey = spec.x_axis;
  const yKey = spec.y_axis;

  // Calculate max value for normalized bar widths
  const values = spec.data.map((d) => Number(d[yKey]) || 0);
  const maxVal = Math.max(...values, 1);

  return (
    <View style={styles.card}>
      <Text style={styles.title}>📊 {spec.title || "Query Visualization"}</Text>
      <View style={styles.chartArea}>
        {spec.data.slice(0, 8).map((item, idx) => {
          const val = Number(item[yKey]) || 0;
          const label = String(item[xKey] ?? `Item ${idx + 1}`);
          const widthPct = `${Math.max(8, (val / maxVal) * 100)}%`;
          const barColor = BAR_COLORS[idx % BAR_COLORS.length];

          return (
            <View key={idx} style={styles.barRow}>
              <Text style={styles.barLabel} numberOfLines={1}>
                {label}
              </Text>
              <View style={styles.barTrack}>
                <View
                  style={[
                    styles.barFill,
                    { width: widthPct as any, backgroundColor: barColor },
                  ]}
                >
                  <Text style={styles.barValue}>{val.toLocaleString()}</Text>
                </View>
              </View>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 8,
    padding: 12,
    marginTop: 8,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  title: {
    fontSize: 12,
    fontWeight: "700",
    color: "#1e293b",
    marginBottom: 10,
  },
  chartArea: {
    gap: 8,
  },
  barRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  barLabel: {
    width: 75,
    fontSize: 10,
    fontWeight: "500",
    color: "#475569",
    textAlign: "right",
  },
  barTrack: {
    flex: 1,
    height: 18,
    backgroundColor: "#f1f5f9",
    borderRadius: 4,
    overflow: "hidden",
    justifyContent: "center",
  },
  barFill: {
    height: "100%",
    borderRadius: 4,
    justifyContent: "center",
    paddingHorizontal: 6,
  },
  barValue: {
    fontSize: 9,
    fontWeight: "700",
    color: "#ffffff",
  },
});
