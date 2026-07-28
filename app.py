"""
app.py — Smart Irrigation System (FULLY FIXED)
================================================
FIXES:
- Continuous readings every 5 seconds (not just once)
- Reading history table updates live in UI
- Pump ON/OFF shows correctly in UI AND controls real Arduino pump
- Stop button instantly kills pump on UI and Arduino
- Terminal + Browser run simultaneously from one command
"""

import os, sys, time, random, json, threading, webbrowser, queue
sys.path.insert(0, os.path.dirname(__file__))

import serial
import serial.tools.list_ports

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from generate_dataset import generate_irrigation_dataset
from preprocess import load_and_preprocess, encode_user_input, IRRIGATION_INV_MAP
from model import train_model, predict_irrigation

app = Flask(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
DATASET_PATH   = os.path.join(os.path.dirname(__file__), "irrigation_data.csv")
PUMP_FLOW_RATE = 1.5   # litres per minute
READ_INTERVAL  = 5     # seconds between readings
BAUD_RATE      = 9600

# ── Global state ───────────────────────────────────────────────────────────────
state = {
    "model":          None,
    "model_accuracy": None,
    "running":        False,
    "pump_on":        False,
    "crop":           None,
    "temperature":    None,
    "humidity":       None,
    "soil_moisture":  None,
    "rain":           None,
    "prediction":     None,
    "confidence":     None,
    "total_water":    0.0,
    "total_readings": 0,
    "pump_cycles":    0,
    "session_start":  None,
    "log":            [],
    "error":          None,
    "arduino_port":   None,
    "hardware_mode":  False,
}

state_lock     = threading.Lock()
sse_clients    = []
monitor_thread = None

# ── Stop event — used to interrupt sleep cleanly ───────────────────────────────
stop_event = threading.Event()

# ── Arduino ────────────────────────────────────────────────────────────────────
def find_arduino():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        if any(k in desc for k in ["arduino", "ch340", "ch341", "ftdi", "usb serial"]):
            return p.device
    return None

def connect_arduino(port):
    try:
        ard = serial.Serial(port, BAUD_RATE, timeout=3)
        time.sleep(2)
        ard.flushInput()
        print(f"[HW] Arduino connected on {port}")
        return ard
    except Exception as e:
        print(f"[!]  Could not connect to {port}: {e}")
        return None

def read_real_sensors(ard):
    try:
        ard.flushInput()
        line = ard.readline().decode("utf-8", errors="ignore").strip()
        if not line or "READY" in line or "ERROR" in line:
            return None
        parts = line.split(",")
        if len(parts) != 3:
            return None
        return float(parts[0]), float(parts[1]), float(parts[2])
    except Exception:
        return None

def send_pump_command(ard, on):
    try:
        ard.write(b'1' if on else b'0')
    except Exception as e:
        print(f"[!] Pump error: {e}")

# ── Sensor simulation ──────────────────────────────────────────────────────────
def simulate_sensors():
    return (
        round(random.uniform(22, 44), 1),
        round(random.uniform(30, 90), 1),
        round(random.uniform(15, 85), 1),
    )

def estimate_rain(temp, hum):
    return "Yes" if hum > 80 and temp < 32 else "No"

# ── Model ──────────────────────────────────────────────────────────────────────
def boot_model():
    print("[..] Training ML model...")
    if not os.path.exists(DATASET_PATH):
        generate_irrigation_dataset(n_samples=600, output_path=DATASET_PATH)
    X, y, _ = load_and_preprocess(DATASET_PATH)
    model, _, _, accuracy = train_model(X, y, model_type="random_forest")
    with state_lock:
        state["model"]          = model
        state["model_accuracy"] = round(accuracy * 100, 2)
    print(f"[OK] Model ready — Accuracy: {accuracy*100:.2f}%")

# ── SSE broadcast ──────────────────────────────────────────────────────────────
def broadcast(event_type, data):
    try:
        payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    except (TypeError, ValueError) as e:
        print(f"[ERROR] JSON serialize failed for {event_type}: {e}")
        # Try again with string-cast fallback
        safe = {k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
                for k, v in data.items()} if isinstance(data, dict) else str(data)
        payload = f"event: {event_type}\ndata: {json.dumps(safe)}\n\n"
    dead = []
    for q in sse_clients:
        try:
            q.put_nowait(payload)
        except Exception:
            dead.append(q)
    for q in dead:
        if q in sse_clients:
            sse_clients.remove(q)

def push_state():
    with state_lock:
        snap = {}
        for k, v in state.items():
            if k in ("model", "log"):
                continue
            # Convert numpy/bool types to plain Python for JSON serialization
            if hasattr(v, 'item'):        # numpy scalar
                v = v.item()
            elif isinstance(v, bool):
                v = bool(v)
            elif isinstance(v, (int, float)) and v != v:  # NaN check
                v = None
            snap[k] = v
    broadcast("state", snap)

# ── Terminal output ────────────────────────────────────────────────────────────
def print_reading(n, temp, hum, rain, soil, crop, pred, conf, pump_on, water, hw):
    tag  = "[HW] " if hw else "[SIM]"
    irr  = "YES — IRRIGATE" if pred == 1 else "NO  — SKIP"
    pump = "PUMP ON  💦" if pump_on else "PUMP OFF 💧"
    print(f"\n{'='*58}")
    print(f"  {tag} Reading #{n}  |  {time.strftime('%H:%M:%S')}")
    print(f"{'='*58}")
    print(f"  Crop          : {crop}")
    print(f"  Temperature   : {temp:.1f} C")
    print(f"  Humidity      : {hum:.1f}%")
    print(f"  Rain Estimate : {rain}")
    print(f"  Soil Moisture : {soil:.0f} / 100")
    print(f"  {'─'*40}")
    print(f"  Irrigation    : {irr}")
    print(f"  Confidence    : {conf:.1f}%")
    print(f"  Status        : {pump}")
    print(f"  Total Water   : {water:.3f} litres")
    print(f"{'='*58}")

def print_summary(cycles, pump_cycles, water, start_time, hw):
    dur  = int(time.time() - start_time)
    mode = "HARDWARE" if hw else "SIMULATION"
    print(f"\n{'='*58}")
    print(f"  SESSION SUMMARY  [{mode}]")
    print(f"{'='*58}")
    print(f"  Total readings  : {cycles}")
    print(f"  Pump ON count   : {pump_cycles}")
    print(f"  Pump OFF count  : {cycles - pump_cycles}")
    print(f"  Total water     : {water:.3f} litres")
    print(f"  Duration        : {dur//60}m {dur%60}s")
    print(f"{'='*58}\n")

# ── Monitoring loop ────────────────────────────────────────────────────────────
def monitoring_loop(crop, port):
    global stop_event

    ard     = None
    hw_mode = False

    if port:
        ard     = connect_arduino(port)
        hw_mode = ard is not None

    print(f"\n{'[HW] HARDWARE MODE' if hw_mode else '[SIM] SIMULATION MODE'} — {crop}")

    # Reset state
    with state_lock:
        state["running"]        = True
        state["crop"]           = crop
        state["hardware_mode"]  = hw_mode
        state["total_water"]    = 0.0
        state["total_readings"] = 0
        state["pump_cycles"]    = 0
        state["session_start"]  = time.time()
        state["log"]            = []
        state["error"]          = None
        state["pump_on"]        = False

    push_state()

    cycle       = 0
    pump_cycles = 0
    total_water = 0.0
    start_time  = time.time()

    print(f"[OK] Readings every {READ_INTERVAL}s — open http://localhost:5000\n")

    try:
        while not stop_event.is_set():

            # Read sensors
            if hw_mode and ard:
                data = read_real_sensors(ard)
                if data is None:
                    print("[..] Waiting for Arduino data...")
                    stop_event.wait(timeout=2)   # interruptible 2s wait
                    continue
                temp, hum, soil = data
            else:
                temp, hum, soil = simulate_sensors()

            rain = estimate_rain(temp, hum)

            # ML prediction
            with state_lock:
                model = state["model"]

            encoded           = encode_user_input(temp, hum, rain, soil, crop)
            prediction, conf  = predict_irrigation(model, encoded)
            pump_on           = (prediction == 1)
            conf_val          = round(conf, 1) if conf else 0.0
            water_this        = round((READ_INTERVAL / 60) * PUMP_FLOW_RATE, 3) if pump_on else 0.0

            cycle += 1
            if pump_on:
                pump_cycles += 1
                total_water  = round(total_water + water_this, 3)

            # Control real pump
            if hw_mode and ard:
                send_pump_command(ard, pump_on)

            # Terminal output
            print_reading(cycle, temp, hum, rain, soil, crop,
                          prediction, conf_val, pump_on, total_water, hw_mode)

            # Log entry
            log_entry = {
                "time":       time.strftime("%H:%M:%S"),
                "temp":       temp,
                "hum":        hum,
                "soil":       soil,
                "rain":       rain,
                "pump":       pump_on,
                "conf":       conf_val,
                "water":      total_water,
                "reading_no": cycle,
                "crop":       crop,
            }

            # Update state
            with state_lock:
                state["temperature"]    = temp
                state["humidity"]       = hum
                state["soil_moisture"]  = soil
                state["rain"]           = rain
                state["prediction"]     = int(prediction)
                state["confidence"]     = conf_val
                state["pump_on"]        = pump_on
                state["total_readings"] = cycle
                state["pump_cycles"]    = pump_cycles
                state["total_water"]    = total_water
                state["log"].insert(0, log_entry)
                if len(state["log"]) > 50:
                    state["log"] = state["log"][:50]

            # Push to browser
            push_state()
            broadcast("log", log_entry)

            # Wait READ_INTERVAL seconds — stop_event.wait() exits immediately when stopped
            stop_event.wait(timeout=READ_INTERVAL)

    except Exception as e:
        print(f"\n[ERROR] {e}")

    finally:
        # Turn pump OFF immediately
        if hw_mode and ard:
            try:
                send_pump_command(ard, False)
                time.sleep(0.1)
                ard.close()
                print("[HW] Pump OFF. Arduino disconnected.")
            except Exception:
                pass

        with state_lock:
            state["running"] = False
            state["pump_on"] = False

        push_state()
        print_summary(cycle, pump_cycles, total_water, start_time, hw_mode)

# ── Flask routes ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/start", methods=["POST"])
def api_start():
    global monitor_thread, stop_event
    data = request.get_json()
    crop = data.get("crop", "Rice")

    with state_lock:
        if state["running"]:
            return jsonify({"status": "already_running"})
        if state["model"] is None:
            return jsonify({"status": "error", "msg": "Model not ready"}), 503
        port = state["arduino_port"]
        hw   = state["hardware_mode"]

    # Fresh stop_event for this session
    stop_event = threading.Event()

    monitor_thread = threading.Thread(
        target=monitoring_loop, args=(crop, port), daemon=True
    )
    monitor_thread.start()
    return jsonify({"status": "started", "crop": crop, "hardware": hw, "port": port})

@app.route("/api/stop", methods=["POST"])
def api_stop():
    global stop_event
    # Signal the monitoring loop to stop immediately
    stop_event.set()
    with state_lock:
        state["running"] = False
        state["pump_on"] = False
    push_state()
    return jsonify({"status": "stopped"})

@app.route("/api/state")
def api_state():
    with state_lock:
        snap = {k: v for k, v in state.items() if k not in ("model", "log")}
    return jsonify(snap)

@app.route("/api/log")
def api_log():
    with state_lock:
        return jsonify(list(state["log"]))

@app.route("/api/model_status")
def api_model_status():
    with state_lock:
        return jsonify({
            "ready":    state["model"] is not None,
            "accuracy": state.get("model_accuracy"),
            "hardware": state.get("hardware_mode", False),
            "port":     state.get("arduino_port"),
        })

@app.route("/stream")
def stream():
    q = queue.Queue(maxsize=100)
    sse_clients.append(q)

    def generate():
        # Send full current state immediately
        with state_lock:
            snap = {k: v for k, v in state.items() if k not in ("model", "log")}
            existing_log = list(state["log"])
        yield f"event: state\ndata: {json.dumps(snap)}\n\n"
        # Replay existing log rows so table is never blank on reconnect
        for entry in reversed(existing_log):
            yield f"event: log\ndata: {json.dumps(entry)}\n\n"

        try:
            while True:
                try:
                    msg = q.get(timeout=15)
                    yield msg
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            if q in sse_clients:
                sse_clients.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )

# ── Startup ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*58)
    print("  SMART IRRIGATION SYSTEM")
    print("="*58)

    # Train model — BLOCKING, wait until fully done
    boot_thread = threading.Thread(target=boot_model, daemon=True)
    boot_thread.start()
    boot_thread.join()

    # Detect Arduino
    print("\n[..] Scanning for Arduino...")
    port = find_arduino()
    if port:
        print(f"[HW] Arduino detected: {port} — Hardware mode ON")
        with state_lock:
            state["arduino_port"]  = port
            state["hardware_mode"] = True
    else:
        print("[SIM] No Arduino — Simulation mode")
        with state_lock:
            state["arduino_port"]  = None
            state["hardware_mode"] = False

    print("\n" + "="*58)
    print("  Select crop in browser → click Start Monitoring")
    print("  Terminal shows every reading in real-time")
    print("  Browser: http://localhost:5000")
    print("="*58 + "\n")

    threading.Thread(
        target=lambda: (time.sleep(1.5), webbrowser.open("http://localhost:5000")),
        daemon=True
    ).start()

    app.run(debug=False, port=5000, threaded=True)
