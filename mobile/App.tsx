import React, { useState, useRef } from "react";
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  StatusBar,
} from "react-native";
import { Message } from "./src/types";
import AgentStepDrawer from "./src/components/AgentStepDrawer";
import ChartViewer from "./src/components/ChartViewer";
import DataDictionaryModal from "./src/components/DataDictionaryModal";
import ServerSettingsModal from "./src/components/ServerSettingsModal";

const INITIAL_MESSAGES: Message[] = [
  {
    id: "welcome",
    sender: "agent",
    text: "👋 Welcome to AskData Mobile!\n\nI am your guarded AI analytics assistant. Every SQL query is inspected by our Java AST Query Guard (Port 8081) on read-only views with customer PII blocked.\n\nTap a quick question below or ask anything!",
    steps: [],
    charts: [],
  },
];

const QUICK_PROMPTS = [
  "What is our current Monthly Recurring Revenue (MRR) in USD?",
  "What is our total net revenue to date in USD?",
  "Which 5 users have executed the highest number of queries?",
  "How are we doing?",
  "SELECT email FROM users",
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [serverUrl, setServerUrl] = useState("http://100.68.39.98:8000");
  const [dictVisible, setDictVisible] = useState(false);
  const [settingsVisible, setSettingsVisible] = useState(false);

  const scrollViewRef = useRef<ScrollView>(null);

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  const handleSend = async (customPrompt?: string) => {
    const q = (customPrompt || inputText).trim();
    if (!q || isLoading) return;

    setInputText("");
    const userMsgId = `user_${Date.now()}`;
    const agentMsgId = `agent_${Date.now()}`;

    // Append user message & loading agent placeholder
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: "user", text: q, steps: [], charts: [] },
      { id: agentMsgId, sender: "agent", text: "Analyzing query & executing guard...", steps: [], charts: [], loading: true },
    ]);
    setIsLoading(true);
    scrollToBottom();

    try {
      // Connect to synchronous endpoint for rock-solid mobile network stability
      const endpoint = `${serverUrl}/chat/sync`;
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, userId: "mobile-user" }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      const answer = data.answer || "Query executed.";
      const steps = data.steps_trace || [];
      const charts = data.charts || [];
      const metrics = data.metrics || undefined;

      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsgId
            ? {
                ...m,
                text: answer,
                steps: steps,
                charts: charts,
                metrics: metrics,
                loading: false,
              }
            : m
        )
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsgId
            ? {
                ...m,
                text: `⚠️ Connection Failed to AskData Backend (${serverUrl}).\n\nEnsure backend is running:\nuvicorn app:app --host 0.0.0.0 --port 8000\n\nError: ${err.message}`,
                loading: false,
              }
            : m
        )
      );
    } finally {
      setIsLoading(false);
      scrollToBottom();
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />

      {/* App Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.logoBadge}>
            <Text style={styles.logoText}>📊</Text>
          </View>
          <View>
            <View style={styles.titleRow}>
              <Text style={styles.appTitle}>AskData Mobile</Text>
              <View style={styles.guardBadge}>
                <Text style={styles.guardBadgeText}>🛡️ Guard 8081</Text>
              </View>
            </View>
            <Text style={styles.appSubtitle}>Gemini 2.5 Flash • AST Guarded</Text>
          </View>
        </View>

        <View style={styles.headerRight}>
          <TouchableOpacity
            style={styles.iconBtn}
            onPress={() => setDictVisible(true)}
          >
            <Text style={styles.iconBtnText}>📖</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.iconBtn}
            onPress={() => setSettingsVisible(true)}
          >
            <Text style={styles.iconBtnText}>⚙️</Text>
          </TouchableOpacity>
        </View>
      </View>

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {/* Messages Stream */}
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
        >
          {messages.map((m) => {
            const isUser = m.sender === "user";
            return (
              <View
                key={m.id}
                style={[
                  styles.msgWrapper,
                  isUser ? styles.msgWrapperUser : styles.msgWrapperAgent,
                ]}
              >
                {!isUser && (
                  <View style={styles.avatarAgent}>
                    <Text style={styles.avatarText}>🤖</Text>
                  </View>
                )}

                <View
                  style={[
                    styles.bubble,
                    isUser ? styles.bubbleUser : styles.bubbleAgent,
                  ]}
                >
                  <Text
                    style={[
                      styles.msgText,
                      isUser ? styles.msgTextUser : styles.msgTextAgent,
                    ]}
                  >
                    {m.text}
                  </Text>

                  {m.loading && (
                    <ActivityIndicator
                      size="small"
                      color="#2563eb"
                      style={{ marginTop: 6 }}
                    />
                  )}

                  {/* Render Charts if any */}
                  {m.charts && m.charts.length > 0 && (
                    <View>
                      {m.charts.map((ch, idx) => (
                        <ChartViewer key={idx} spec={ch} />
                      ))}
                    </View>
                  )}

                  {/* Collapsible Steps Drawer */}
                  {m.steps && m.steps.length > 0 && (
                    <AgentStepDrawer steps={m.steps} metrics={m.metrics} />
                  )}
                </View>
              </View>
            );
          })}
        </ScrollView>

        {/* Quick Prompts Bar */}
        <View style={styles.quickBar}>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.quickBarContent}
          >
            {QUICK_PROMPTS.map((p, idx) => (
              <TouchableOpacity
                key={idx}
                style={styles.quickPill}
                onPress={() => handleSend(p)}
                disabled={isLoading}
              >
                <Text style={styles.quickPillText} numberOfLines={1}>
                  {p}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* Input Bar */}
        <View style={styles.inputBar}>
          <TextInput
            style={styles.input}
            value={inputText}
            onChangeText={setInputText}
            placeholder="Ask an analytics question..."
            placeholderTextColor="#94a3b8"
            editable={!isLoading}
          />
          <TouchableOpacity
            style={[styles.sendBtn, (!inputText.trim() || isLoading) && styles.sendBtnDisabled]}
            onPress={() => handleSend()}
            disabled={!inputText.trim() || isLoading}
          >
            {isLoading ? (
              <ActivityIndicator size="small" color="#ffffff" />
            ) : (
              <Text style={styles.sendBtnText}>Ask</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* Schema Dictionary Modal */}
      <DataDictionaryModal
        visible={dictVisible}
        onClose={() => setDictVisible(false)}
      />

      {/* Server Settings Modal */}
      <ServerSettingsModal
        visible={settingsVisible}
        currentUrl={serverUrl}
        onSave={setServerUrl}
        onClose={() => setSettingsVisible(false)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
  flex: {
    flex: 1,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#e2e8f0",
    backgroundColor: "#ffffff",
  },
  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  logoBadge: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: "#2563eb",
    justifyContent: "center",
    alignItems: "center",
  },
  logoText: {
    fontSize: 18,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  appTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#0f172a",
  },
  guardBadge: {
    backgroundColor: "#dcfce7",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
  },
  guardBadgeText: {
    fontSize: 9,
    fontWeight: "700",
    color: "#166534",
  },
  appSubtitle: {
    fontSize: 10,
    color: "#64748b",
  },
  headerRight: {
    flexDirection: "row",
    gap: 6,
  },
  iconBtn: {
    width: 34,
    height: 34,
    borderRadius: 6,
    backgroundColor: "#f1f5f9",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  iconBtnText: {
    fontSize: 14,
  },
  messagesContainer: {
    flex: 1,
    backgroundColor: "#f8fafc",
  },
  messagesContent: {
    padding: 14,
    gap: 12,
  },
  msgWrapper: {
    flexDirection: "row",
    gap: 8,
  },
  msgWrapperUser: {
    justifyContent: "flex-end",
  },
  msgWrapperAgent: {
    justifyContent: "flex-start",
  },
  avatarAgent: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "#2563eb",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 2,
  },
  avatarText: {
    fontSize: 14,
  },
  bubble: {
    maxWidth: "85%",
    borderRadius: 14,
    padding: 12,
  },
  bubbleUser: {
    backgroundColor: "#2563eb",
    borderBottomRightRadius: 2,
  },
  bubbleAgent: {
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#e2e8f0",
    borderBottomLeftRadius: 2,
  },
  msgText: {
    fontSize: 13,
    lineHeight: 19,
  },
  msgTextUser: {
    color: "#ffffff",
  },
  msgTextAgent: {
    color: "#0f172a",
  },
  quickBar: {
    backgroundColor: "#f1f5f9",
    borderTopWidth: 1,
    borderTopColor: "#e2e8f0",
    paddingVertical: 6,
  },
  quickBarContent: {
    paddingHorizontal: 12,
    gap: 6,
  },
  quickPill: {
    backgroundColor: "#ffffff",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#cbd5e1",
    maxWidth: 240,
  },
  quickPillText: {
    fontSize: 11,
    color: "#475569",
    fontWeight: "500",
  },
  inputBar: {
    flexDirection: "row",
    padding: 10,
    backgroundColor: "#ffffff",
    borderTopWidth: 1,
    borderTopColor: "#e2e8f0",
    gap: 8,
  },
  input: {
    flex: 1,
    backgroundColor: "#f8fafc",
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    fontSize: 13,
    color: "#0f172a",
  },
  sendBtn: {
    backgroundColor: "#2563eb",
    borderRadius: 20,
    paddingHorizontal: 16,
    justifyContent: "center",
    alignItems: "center",
  },
  sendBtnDisabled: {
    opacity: 0.5,
  },
  sendBtnText: {
    color: "#ffffff",
    fontWeight: "600",
    fontSize: 13,
  },
});
