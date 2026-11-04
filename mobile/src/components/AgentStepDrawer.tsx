import React, { useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from "react-native";
import { Step } from "../types";

interface Props {
  steps: Step[];
  metrics?: any;
}

export default function AgentStepDrawer({ steps, metrics }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  if (!steps || steps.length === 0) return null;

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.header}
        onPress={() => setIsOpen(!isOpen)}
        activeOpacity={0.7}
      >
        <Text style={styles.headerTitle}>
          ⚙️ Agent Reasoning ({steps.length} events)
        </Text>
        <Text style={styles.chevron}>{isOpen ? "▲" : "▼"}</Text>
      </TouchableOpacity>

      {metrics && (
        <View style={styles.metricsBar}>
          <Text style={styles.metricText}>⏱️ {metrics.total_steps || 0} steps</Text>
          <Text style={styles.metricText}>🪙 {metrics.total_tokens || 0} tok</Text>
          <Text style={styles.metricCost}>
            💵 ${(metrics.estimated_cost_usd || 0).toFixed(5)}
          </Text>
        </View>
      )}

      {isOpen && (
        <View style={styles.body}>
          {steps.map((st, i) => {
            if (st.type === "tool_call") {
              return (
                <View key={i} style={styles.stepBox}>
                  <Text style={styles.stepTitle}>
                    Step {st.step}: Calling Tool [{st.tool}]
                  </Text>
                  {st.thought ? (
                    <Text style={styles.thoughtText}>"{st.thought}"</Text>
                  ) : null}

                  {st.tool === "run_query" && st.arguments?.sql ? (
                    <View style={styles.sqlBox}>
                      <Text style={styles.sqlText}>{st.arguments.sql}</Text>
                    </View>
                  ) : (
                    <Text style={styles.argsText}>
                      {JSON.stringify(st.arguments, null, 2)}
                    </Text>
                  )}
                </View>
              );
            }

            if (st.type === "tool_result") {
              const res = st.result;
              const isSuccess = res?.success !== false;
              return (
                <View
                  key={i}
                  style={[
                    styles.resultBox,
                    isSuccess ? styles.resultSuccess : styles.resultError,
                  ]}
                >
                  <Text
                    style={[
                      styles.resultStatus,
                      isSuccess ? styles.statusSuccess : styles.statusError,
                    ]}
                  >
                    {isSuccess
                      ? `✓ Guard Approved (${res?.executionTimeMs || 0}ms)`
                      : "✗ Guard Rejected Query"}
                  </Text>
                  {res?.rowCount !== undefined && (
                    <Text style={styles.rowsCount}>
                      {res.rowCount} row(s) returned
                    </Text>
                  )}
                  {res?.error && (
                    <Text style={styles.errorMsg}>{res.error}</Text>
                  )}
                </View>
              );
            }

            if (st.type === "guard_rejection") {
              return (
                <View key={i} style={styles.rejectionBox}>
                  <Text style={styles.rejectionText}>
                    🛡️ Self-Correction: {st.rejection}
                  </Text>
                </View>
              );
            }

            return null;
          })}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 8,
    borderRadius: 8,
    backgroundColor: "#f8fafc",
    borderWidth: 1,
    borderColor: "#e2e8f0",
    overflow: "hidden",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: "#f1f5f9",
  },
  headerTitle: {
    fontSize: 12,
    fontWeight: "600",
    color: "#334155",
  },
  chevron: {
    fontSize: 10,
    color: "#64748b",
  },
  metricsBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: 4,
    backgroundColor: "#e2e8f0",
  },
  metricText: {
    fontSize: 10,
    color: "#475569",
    fontFamily: "monospace",
  },
  metricCost: {
    fontSize: 10,
    color: "#166534",
    fontWeight: "700",
    fontFamily: "monospace",
  },
  body: {
    padding: 10,
    gap: 8,
  },
  stepBox: {
    backgroundColor: "#ffffff",
    padding: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#cbd5e1",
  },
  stepTitle: {
    fontSize: 11,
    fontWeight: "700",
    color: "#2563eb",
    marginBottom: 4,
  },
  thoughtText: {
    fontSize: 11,
    fontStyle: "italic",
    color: "#64748b",
    marginBottom: 6,
  },
  sqlBox: {
    backgroundColor: "#0f172a",
    padding: 8,
    borderRadius: 4,
  },
  sqlText: {
    color: "#34d399",
    fontFamily: "monospace",
    fontSize: 10,
    lineHeight: 14,
  },
  argsText: {
    fontSize: 10,
    fontFamily: "monospace",
    color: "#334155",
  },
  resultBox: {
    padding: 8,
    borderRadius: 6,
    borderLeftWidth: 3,
  },
  resultSuccess: {
    backgroundColor: "#f0fdf4",
    borderLeftColor: "#16a34a",
  },
  resultError: {
    backgroundColor: "#fef2f2",
    borderLeftColor: "#dc2626",
  },
  resultStatus: {
    fontSize: 11,
    fontWeight: "700",
  },
  statusSuccess: {
    color: "#166534",
  },
  statusError: {
    color: "#991b1b",
  },
  rowsCount: {
    fontSize: 10,
    color: "#64748b",
    marginTop: 2,
  },
  errorMsg: {
    fontSize: 10,
    color: "#dc2626",
    fontFamily: "monospace",
    marginTop: 2,
  },
  rejectionBox: {
    padding: 6,
    backgroundColor: "#fff1f2",
    borderRadius: 4,
    borderWidth: 1,
    borderColor: "#fecdd3",
  },
  rejectionText: {
    fontSize: 10,
    color: "#9f1239",
    fontWeight: "500",
  },
});
