/*
  arduino_sensors.ino
  Smart Irrigation System - Sensor Reader
  ----------------------------------------
  Reads DHT11 (Temp + Humidity) and Soil Moisture sensor.
  Sends data to laptop via USB Serial every 3 seconds.
  Receives pump command from Python (1=ON, 0=OFF).

  Wiring:
    DHT11  DATA  -> Pin 2
    DHT11  VCC   -> 5V
    DHT11  GND   -> GND
    Soil   AO    -> A0
    Soil   VCC   -> 5V
    Soil   GND   -> GND
    Relay  IN    -> Pin 7
    Relay  VCC   -> 5V
    Relay  GND   -> GND
*/

#include <DHT.h>

#define DHT_PIN    2
#define DHT_TYPE   DHT11
#define SOIL_PIN   A0
#define RELAY_PIN  7

DHT dht(DHT_PIN, DHT_TYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  delay(2000);
  Serial.println("READY");
}

void loop() {

  // Read temperature and humidity
  float temperature = dht.readTemperature();
  float humidity    = dht.readHumidity();

  // Check if reading failed
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("ERROR:DHT");
    delay(2000);
    return;
  }

  // Read soil moisture
  // Raw: 0 (wet) to 1023 (dry) -> convert to 0-100 scale
  int raw   = analogRead(SOIL_PIN);
  int soil  = map(raw, 1023, 300, 0, 100);
  soil      = constrain(soil, 0, 100);

  // Send to Python: temperature,humidity,soil_moisture
  Serial.print(temperature);
  Serial.print(",");
  Serial.print(humidity);
  Serial.print(",");
  Serial.println(soil);

  // Check if Python sent pump command
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == '1') {
      digitalWrite(RELAY_PIN, HIGH);  // Pump ON
    } else if (cmd == '0') {
      digitalWrite(RELAY_PIN, LOW);   // Pump OFF
    }
  }

  delay(3000);
}
