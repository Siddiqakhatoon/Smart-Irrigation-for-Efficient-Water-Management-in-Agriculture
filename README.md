# 🌱 Smart Irrigation System — AI + Web UI
### Machine Learning | Real-time Dashboard | Telugu / Hindi / English | Simulation Mode

---

## 📁 Project Structure
```
smart_irrigation/
├── app.py                ← Flask web server (NEW — run this)
├── main_cli.py           ← Original CLI version (still works)
├── generate_dataset.py   ← Synthetic dataset generator
├── preprocess.py         ← Data loading & encoding
├── model.py              ← ML training & prediction
├── irrigation_data.csv   ← Auto-generated dataset (600 rows)
├── requirements.txt      ← Python dependencies
├── arduino_sensors.ino   ← Upload to Arduino (unchanged)
└── templates/
    └── index.html        ← Web UI (farmer-friendly)
```

---

## ⚙️ Setup (One Time)

### Step 1 — Install Python (if not installed)
Download Python 3.11 from https://python.org  
✅ Check "Add Python to PATH" during install

### Step 2 — Open Command Prompt / Terminal
- **Windows**: Press `Win + R` → type `cmd` → Enter
- **VS Code**: Open the folder in VS Code → press `` Ctrl+` `` to open terminal

### Step 3 — Navigate to project folder
```bash
cd C:\path\to\smart_irrigation
```
(Replace with your actual folder path)

### Step 4 — Install dependencies
```bash
pip install -r requirements.txt
```

---

## ▶️ How to Run

### Option A — Web UI (Recommended for farmers)
```bash
python app.py
```
Then open your browser and go to:
```
http://localhost:5000
```
The system will:
1. Train the ML model automatically on startup (~5 seconds)
2. Show the web dashboard
3. Run in **Simulation Mode** (no Arduino needed!)

---

### Option B — Command Line (Original)
```bash
python main_cli.py
```
This runs the original text-based terminal version.  
Requires Arduino connected via USB.

---

## 🌾 Using the Web UI

### Step 1 — Select Crop
Click on **Rice 🌾**, **Wheat 🌿**, or **Cotton 🌸**

OR say the crop name using the 🎤 Voice button:
- English: "Rice" / "Wheat" / "Cotton"
- Telugu: "వరి" / "గోధుమ" / "పత్తి"
- Hindi: "धान" / "गेहूं" / "कपास"

### Step 2 — Change Language (optional)
Click **EN** / **తె** / **हि** in the top right to switch language

### Step 3 — Start Monitoring
Click **▶ Start Monitoring**

The dashboard will show live:
- 🌡️ Temperature, 💨 Humidity, 🌱 Soil Moisture
- 🚿 Pump ON / 💧 Pump OFF status
- ML prediction with confidence %
- Water usage in litres
- Reading history table

### Step 4 — Stop
Click **⏹ Stop** at any time

---

## 🔌 With Real Arduino (Optional)
The UI runs in Simulation Mode by default.  
If you have the Arduino connected:
1. Upload `arduino_sensors.ino` to your Arduino
2. In `app.py`, find the `/api/start` route and set `use_arduino=True`  
   OR modify the start call in `index.html` to pass `"use_arduino": true`

---

## 🌐 Running on VS Code
1. Open VS Code
2. File → Open Folder → select `smart_irrigation/`
3. Open terminal: `Ctrl + `` ` ``
4. Run: `python app.py`
5. Click the link that appears, or go to `http://localhost:5000`

---

## 🌐 Access from Phone (Same WiFi)
If you want to open the UI on a phone/tablet on the same network:
1. Find your computer's local IP: run `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
2. Open browser on phone: `http://192.168.x.x:5000`

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: flask` | Run `pip install flask` |
| Port 5000 already in use | Change port in app.py: `app.run(port=5001)` |
| Voice not working | Use Google Chrome browser |
| Model takes long to load | Wait 5-10 seconds on first run |
| Dataset not found | It auto-generates on first run |

---

## 🔮 Languages Supported
| Language | Crop Names | UI Labels | Voice |
|----------|-----------|-----------|-------|
| English  | Rice, Wheat, Cotton | ✅ | ✅ |
| Telugu   | వరి, గోధుమ, పత్తి | ✅ | ✅ |
| Hindi    | धान, गेहूं, कपास | ✅ | ✅ |
