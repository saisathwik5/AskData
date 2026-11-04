import React, { useState } from "react";
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from "react-native";

interface Props {
  visible: boolean;
  currentUrl: string;
  onSave: (url: string) => void;
  onClose: () => void;
}

const PRESETS = [
  { label: "Wi-Fi (Real Phone)", url: "http://100.68.39.98:8000" },
  { label: "Android Emulator", url: "http://10.0.2.2:8000" },
  { label: "Localhost (Web/iOS)", url: "http://localhost:8000" },
];

export default function ServerSettingsModal({
  visible,
  currentUrl,
  onSave,
  onClose,
}: Props) {
  const [url, setUrl] = useState(currentUrl);

  const handleSave = () => {
    let clean = url.trim();
    if (clean.endsWith("/")) clean = clean.slice(0, -1);
    onSave(clean);
    onClose();
  };

  return (
    <Modal visible={visible} animationType="fade" transparent>
      <View style={styles.overlay}>
        <View style={styles.modalBox}>
          <Text style={styles.title}>🌐 Backend Connection Settings</Text>
          <Text style={styles.subtitle}>
            Enter the address of your AskData Python FastAPI backend server:
          </Text>

          <TextInput
            style={styles.input}
            value={url}
            onChangeText={setUrl}
            placeholder="http://100.68.39.98:8000"
            autoCapitalize="none"
            autoCorrect={false}
          />

          <Text style={styles.presetsHeader}>QUICK PRESETS:</Text>
          <View style={styles.presetsRow}>
            {PRESETS.map((p, idx) => (
              <TouchableOpacity
                key={idx}
                style={styles.presetBtn}
                onPress={() => setUrl(p.url)}
              >
                <Text style={styles.presetText}>{p.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <View style={styles.btnRow}>
            <TouchableOpacity style={styles.cancelBtn} onPress={onClose}>
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.saveBtn} onPress={handleSave}>
              <Text style={styles.saveText}>Save URL</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(15, 23, 42, 0.6)",
    justifyContent: "center",
    padding: 20,
  },
  modalBox: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 20,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 10,
    elevation: 6,
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0f172a",
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 12,
    color: "#64748b",
    marginBottom: 14,
    lineHeight: 18,
  },
  input: {
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 8,
    padding: 10,
    fontSize: 13,
    fontFamily: "monospace",
    backgroundColor: "#f8fafc",
    marginBottom: 14,
  },
  presetsHeader: {
    fontSize: 10,
    fontWeight: "700",
    color: "#94a3b8",
    marginBottom: 8,
  },
  presetsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginBottom: 18,
  },
  presetBtn: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    backgroundColor: "#f1f5f9",
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  presetText: {
    fontSize: 11,
    color: "#334155",
    fontWeight: "500",
  },
  btnRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 10,
  },
  cancelBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
  },
  cancelText: {
    fontSize: 13,
    color: "#64748b",
    fontWeight: "600",
  },
  saveBtn: {
    backgroundColor: "#2563eb",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
  },
  saveText: {
    fontSize: 13,
    color: "#ffffff",
    fontWeight: "600",
  },
});
