import sys
import os
import time
import serial
import serial.tools.list_ports

sys.path.insert(0, os.path.dirname(__file__))

from generate_dataset import generate_irrigation_dataset
from preprocess import load_and_preprocess, encode_user_input, IRRIGATION_INV_MAP, CROP_MAP
from model import train_model, predict_irrigation

DATASET_PATH   = os.path.join(os.path.dirname(__file__), "irrigation_data.csv")
MODEL_TYPE     = "random_forest"
BAUD_RATE      = 9600
READ_INTERVAL  = 5       # seconds between readings
PUMP_FLOW_RATE = 1.5     # litres per minute (adjust for your pump)


def print_banner():
    print("\n" + "=" * 58)
    print("   SMART IRRIGATION SYSTEM")
    print("   Live Sensor Mode | Arduino + ML")
    print("   Region: Telangana, India")
    print("=" * 58 + "\n")


def estimate_rain(temperature, humidity):
    if humidity > 80 and temperature < 32:
        return "Yes"
    return "No"


def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        desc = port.description.lower()
        if "arduino" in desc or "ch340" in desc or "usb" in desc or "serial" in desc:
            print(f"[OK] Arduino found: {port.device}")
            return port.device

    print("\n[!] Arduino not auto-detected. Available ports:")
    for i, port in enumerate(ports):
        print(f"    {i+1}. {port.device} - {port.description}")

    if not ports:
        print("    No ports found! Check USB cable.")
        return None

    choice = input("\n    Type port number: ").strip()
    try:
        return ports[int(choice) - 1].device
    except:
        return None


def connect_arduino(port):
    try:
        arduino = serial.Serial(port, BAUD_RATE, timeout=5)
        time.sleep(2)
        print(f"[OK] Connected to {port}")
        return arduino
    except Exception as e:
        print(f"[ERROR] Cannot connect: {e}")
        return None


def read_sensors(arduino):
    try:
        arduino.flushInput()
        line = arduino.readline().decode('utf-8').strip()

        if not line or "READY" in line or "ERROR" in line:
            return None

        parts = line.split(",")
        if len(parts) != 3:
            return None

        temperature   = float(parts[0])
        humidity      = float(parts[1])
        soil_moisture = float(parts[2])
        return temperature, humidity, soil_moisture

    except Exception as e:
        print(f"[!] Read error: {e}")
        return None


def control_pump(arduino, prediction):
    cmd = b'1' if prediction == 1 else b'0'
    arduino.write(cmd)


def get_crop_type():
    valid = list(CROP_MAP.keys())
    while True:
        print(f"\n   Crops available: {', '.join(valid)}")
        crop = input("   Enter crop type: ").strip().capitalize()
        if crop in valid:
            return crop
        print(f"   [!] Choose from: {valid}")


def calculate_water(pump_on_seconds):
    """
    Calculates water used based on how long pump was ON.
    Formula: litres = (seconds / 60) * flow_rate
    Default flow rate = 1.5 litres per minute
    """
    litres = (pump_on_seconds / 60) * PUMP_FLOW_RATE
    return round(litres, 3)


def show_results(temp, hum, rain, sm, crop, prediction, confidence,
                 cycle, pump_on_seconds, total_water):
    label = IRRIGATION_INV_MAP[prediction]
    conf  = f"{confidence:.1f}%" if confidence else "N/A"

    print(f"\n{'='*58}")
    print(f"   READING #{cycle}  |  {time.strftime('%H:%M:%S')}")
    print(f"{'='*58}")
    print(f"   Temperature    : {temp:.1f} C")
    print(f"   Humidity       : {hum:.1f}%")
    print(f"   Rain Estimated : {rain}")
    print(f"   Soil Moisture  : {sm:.0f} / 100")
    print(f"   Crop           : {crop}")
    print(f"{'-'*58}")
    print(f"   Irrigation     : {label}")
    print(f"   Confidence     : {conf}")
    print(f"{'-'*58}")

    if prediction == 1:
        session_water = calculate_water(READ_INTERVAL)
        print(f"   >>> PUMP ON  - Start irrigation!")
        print(f"   Water this cycle : {session_water:.3f} litres")
        print(f"   Total water used : {total_water:.3f} litres")
    else:
        print(f"   >>> PUMP OFF - No irrigation needed.")
        print(f"   Total water used : {total_water:.3f} litres")

    print(f"{'='*58}")


def show_summary(total_cycles, pump_cycles, total_water, start_time):
    """Shows full session summary when user stops with Ctrl+C."""
    duration = int(time.time() - start_time)
    mins = duration // 60
    secs = duration % 60

    print(f"\n{'='*58}")
    print(f"   SESSION SUMMARY")
    print(f"{'='*58}")
    print(f"   Total readings     : {total_cycles}")
    print(f"   Pump ON count      : {pump_cycles}")
    print(f"   Pump OFF count     : {total_cycles - pump_cycles}")
    print(f"   Total water used   : {total_water:.3f} litres")
    print(f"   Session duration   : {mins}m {secs}s")
    print(f"{'='*58}\n")


def main():
    print_banner()

    # Step 1 - Train ML model
    print("[1/3] Loading dataset and training model...")
    X, y, df = load_and_preprocess(DATASET_PATH)
    model, X_test, y_test, accuracy = train_model(X, y, model_type=MODEL_TYPE)
    print(f"[OK] Model trained. Accuracy: {accuracy * 100:.2f}%")

    # Step 2 - Connect Arduino
    print("\n[2/3] Connecting to Arduino...")
    port = find_arduino_port()
    if not port:
        print("[ERROR] Arduino not found. Check USB cable.")
        return

    arduino = connect_arduino(port)
    if not arduino:
        return

    # Step 3 - Get crop type once
    print("\n[3/3] Almost ready...")
    crop = get_crop_type()

    print(f"\n[OK] Crop     : {crop}")
    print(f"[OK] Interval : every {READ_INTERVAL} seconds")
    print(f"[OK] Flow rate: {PUMP_FLOW_RATE} L/min")
    print("     Press Ctrl+C to stop.\n")

    # Tracking variables
    cycle        = 0
    pump_cycles  = 0
    total_water  = 0.0
    start_time   = time.time()

    try:
        while True:
            cycle += 1

            # Read from Arduino
            data = read_sensors(arduino)
            if data is None:
                print("[..] Waiting for sensor data...")
                time.sleep(2)
                continue

            temp, hum, sm = data
            rain = estimate_rain(temp, hum)

            # ML prediction
            encoded = encode_user_input(temp, hum, rain, sm, crop)
            prediction, confidence = predict_irrigation(model, encoded)

            # Track water usage
            if prediction == 1:
                pump_cycles += 1
                total_water += calculate_water(READ_INTERVAL)

            # Show results
            show_results(temp, hum, rain, sm, crop,
                         prediction, confidence,
                         cycle, READ_INTERVAL, total_water)

            # Control pump
            control_pump(arduino, prediction)

            # Wait
            time.sleep(READ_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[OK] Shutting down...")
        control_pump(arduino, 0)
        arduino.close()
        show_summary(cycle, pump_cycles, total_water, start_time)
        print("[OK] Pump OFF. System stopped. Goodbye!\n")


if __name__ == "__main__":
    main()
