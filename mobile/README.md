# AskData Mobile (React Native + Expo)

The cross-platform mobile application for **AskData** — available for both **iOS and Android**.

---

## 📱 Features

1. **Native Mobile Conversational Interface:** Responsive chat layout built for mobile screens with real-time feedback.
2. **Collapsible "Agent Reasoning" Drawer:** Inspect step-by-step model thoughts, AST-approved SQL, execution time (in ms), token counts, and cost.
3. **Interactive Mobile Charts:** Visualizes analytical query outcomes with proportional horizontal bar graphs and metrics.
4. **Interactive Schema Dictionary Sheet:** Inspect database columns, data types, and sample data for `v_users`, `v_subscriptions`, `v_payments`, and `v_events`.
5. **Configurable Server Settings:** Tap the ⚙️ icon in the app header to switch between your computer's local Wi-Fi IP (`http://100.68.39.98:8000`), Android Emulator (`http://10.0.2.2:8000`), or `http://localhost:8000`.

---

## 🚀 How to Run & Test

### Step 1: Start the Backend Services on Your Computer

1. **Start the Java Query Guard (Port 8081):**
   ```powershell
   cd AskData\guard
   mvn spring-boot:run
   ```

2. **Start the Python Agent API (Port 8000 on `0.0.0.0`):**
   *(Note: Binding to `0.0.0.0` allows your mobile phone on the same Wi-Fi network to connect).*
   ```powershell
   cd AskData\agent
   uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

---

### Step 2: Start the Mobile App

In a new terminal:
```powershell
cd AskData\mobile
npm install
npx expo start
```

---

### Step 3: View on Your Phone or Emulator

#### Option A: On Your Real Physical Phone (iPhone or Android)
1. Download the free **Expo Go** app from the [Apple App Store](https://apps.apple.com/app/expo-go/id982107779) or [Google Play Store](https://play.google.com/store/apps/details?id=host.exp.exponent).
2. Ensure your phone is connected to the **same Wi-Fi network** as your laptop.
3. Open your phone camera (iOS) or the Expo Go app (Android) and **scan the QR code** displayed in your terminal.
4. The AskData mobile app will load instantly on your phone!

#### Option B: On Android Emulator
Press `a` in the terminal running Expo.

#### Option C: On Web Browser
Press `w` in the terminal running Expo.
