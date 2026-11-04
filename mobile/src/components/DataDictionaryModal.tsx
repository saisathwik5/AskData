import React, { useState } from "react";
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  SafeAreaView,
} from "react-native";
import { TableViewDef } from "../types";

const DICTIONARY: TableViewDef[] = [
  {
    name: "v_users",
    description: "Customer accounts view. Sensitive PII (email, full_name) removed at database view level.",
    rowCount: "2,000 rows",
    columns: [
      { name: "id", type: "VARCHAR(36)", description: "Primary Key UUID", sample: "335a5132-..." },
      { name: "country", type: "VARCHAR(2)", description: "ISO 2-letter country code (can be NULL)", sample: "US, CA, GB" },
      { name: "signup_date", type: "TIMESTAMPTZ", description: "Account creation timestamp", sample: "2024-03-15T14:22:00Z" },
      { name: "plan", type: "VARCHAR(50)", description: "Initial chosen tier", sample: "starter, pro, enterprise" },
      { name: "is_test_account", type: "BOOLEAN", description: "Internal test account. Exclude from revenue metrics!", sample: "FALSE, TRUE" },
    ],
  },
  {
    name: "v_subscriptions",
    description: "Customer subscription tier lifecycle statuses and billing dates.",
    rowCount: "2,037 rows",
    columns: [
      { name: "id", type: "VARCHAR(36)", description: "Subscription UUID", sample: "s-48192" },
      { name: "user_id", type: "VARCHAR(36)", description: "Foreign key to v_users(id)", sample: "u-1234" },
      { name: "plan", type: "VARCHAR(50)", description: "Starter ($29), Pro ($99), Enterprise ($499)", sample: "starter, pro, enterprise" },
      { name: "status", type: "VARCHAR(50)", description: "active, canceled, trialing", sample: "active, canceled" },
      { name: "start_date", type: "TIMESTAMPTZ", description: "Start timestamp", sample: "2024-01-15T00:00:00Z" },
      { name: "end_date", type: "TIMESTAMPTZ", description: "Cancellation date (NULL if active)", sample: "NULL" },
    ],
  },
  {
    name: "v_payments",
    description: "Transaction charges and refund deductions. Currencies: USD or EUR.",
    rowCount: "13,142 rows",
    columns: [
      { name: "amount", type: "NUMERIC(10,2)", description: "Gross billed amount", sample: "29.00, 99.00" },
      { name: "currency", type: "VARCHAR(3)", description: "USD or EUR (Never sum across currencies!)", sample: "USD, EUR" },
      { name: "status", type: "VARCHAR(50)", description: "succeeded, failed, refunded", sample: "succeeded" },
      { name: "refunded_amount", type: "NUMERIC(10,2)", description: "Refund portion (subtract for Net Rev)", sample: "0.00, 99.00" },
    ],
  },
  {
    name: "v_events",
    description: "High-volume user event stream (100k rows). event_name='query_executed'.",
    rowCount: "100,000 rows",
    columns: [
      { name: "event_name", type: "VARCHAR(100)", description: "Action name", sample: "page_view, query_executed" },
      { name: "occurred_at", type: "TIMESTAMPTZ", description: "Timestamp", sample: "2024-08-12T19:40:00Z" },
      { name: "properties", type: "JSONB", description: "Metadata JSON", sample: "{\"browser\":\"Chrome\"}" },
    ],
  },
];

interface Props {
  visible: boolean;
  onClose: () => void;
}

export default function DataDictionaryModal({ visible, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<string>("v_users");
  const currentTable = DICTIONARY.find((t) => t.name === activeTab) || DICTIONARY[0];

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
      <SafeAreaView style={styles.modalContainer}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>📖 Schema Dictionary</Text>
          <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
            <Text style={styles.closeBtnText}>Done</Text>
          </TouchableOpacity>
        </View>

        {/* Table Selection Tabs */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.tabsContainer}
          contentContainerStyle={styles.tabsContent}
        >
          {DICTIONARY.map((tbl) => (
            <TouchableOpacity
              key={tbl.name}
              style={[
                styles.tabBtn,
                activeTab === tbl.name && styles.tabBtnActive,
              ]}
              onPress={() => setActiveTab(tbl.name)}
            >
              <Text
                style={[
                  styles.tabText,
                  activeTab === tbl.name && styles.tabTextActive,
                ]}
              >
                {tbl.name}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Content */}
        <ScrollView style={styles.body}>
          <View style={styles.tableHeader}>
            <Text style={styles.tableName}>{currentTable.name}</Text>
            <Text style={styles.rowCountBadge}>{currentTable.rowCount}</Text>
          </View>
          <Text style={styles.tableDesc}>{currentTable.description}</Text>

          {currentTable.name === "v_users" && (
            <View style={styles.piiWarning}>
              <Text style={styles.piiWarningText}>
                🛡️ PII Guard: Direct customer email and full_name are blocked at both database view & Java Guard AST levels.
              </Text>
            </View>
          )}

          <Text style={styles.sectionTitle}>COLUMNS</Text>
          {currentTable.columns.map((col, idx) => (
            <View key={idx} style={styles.columnCard}>
              <View style={styles.colTopRow}>
                <Text style={styles.colName}>{col.name}</Text>
                <Text style={styles.colType}>{col.type}</Text>
              </View>
              <Text style={styles.colDesc}>{col.description}</Text>
              {col.sample && (
                <Text style={styles.colSample}>Sample: {col.sample}</Text>
              )}
            </View>
          ))}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalContainer: {
    flex: 1,
    backgroundColor: "#f8fafc",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#e2e8f0",
    backgroundColor: "#ffffff",
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0f172a",
  },
  closeBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: "#2563eb",
  },
  closeBtnText: {
    color: "#ffffff",
    fontWeight: "600",
    fontSize: 13,
  },
  tabsContainer: {
    maxHeight: 46,
    backgroundColor: "#ffffff",
    borderBottomWidth: 1,
    borderBottomColor: "#e2e8f0",
  },
  tabsContent: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    gap: 8,
  },
  tabBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: "#f1f5f9",
  },
  tabBtnActive: {
    backgroundColor: "#2563eb",
  },
  tabText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#475569",
    fontFamily: "monospace",
  },
  tabTextActive: {
    color: "#ffffff",
  },
  body: {
    flex: 1,
    padding: 16,
  },
  tableHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  tableName: {
    fontSize: 18,
    fontWeight: "700",
    fontFamily: "monospace",
    color: "#1e3a8a",
  },
  rowCountBadge: {
    fontSize: 11,
    fontWeight: "600",
    backgroundColor: "#e2e8f0",
    color: "#475569",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  tableDesc: {
    fontSize: 12,
    color: "#64748b",
    marginBottom: 12,
    lineHeight: 18,
  },
  piiWarning: {
    backgroundColor: "#ecfdf5",
    borderWidth: 1,
    borderColor: "#a7f3d0",
    padding: 10,
    borderRadius: 8,
    marginBottom: 14,
  },
  piiWarningText: {
    fontSize: 11,
    color: "#065f46",
    lineHeight: 16,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: "700",
    color: "#94a3b8",
    letterSpacing: 1,
    marginBottom: 8,
  },
  columnCard: {
    backgroundColor: "#ffffff",
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  colTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  colName: {
    fontSize: 13,
    fontWeight: "700",
    fontFamily: "monospace",
    color: "#2563eb",
  },
  colType: {
    fontSize: 10,
    fontFamily: "monospace",
    color: "#64748b",
  },
  colDesc: {
    fontSize: 11,
    color: "#334155",
    lineHeight: 16,
  },
  colSample: {
    fontSize: 10,
    fontFamily: "monospace",
    color: "#94a3b8",
    marginTop: 4,
  },
});
