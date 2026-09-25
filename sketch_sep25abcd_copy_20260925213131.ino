// Full Firmware: Occupancy-Aware IoT Energy Monitoring System
// Integrates: ACS712 (current), ZMPT101B (voltage), DS18B20 (temperature),
// PIR (occupancy), 4-channel relay, SSD1306 OLED, Wi-Fi + Firebase RTDB

#include <WiFi.h>
#include <Firebase_ESP_Client.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ZMPT101B.h>
#include <ACS712.h>

// ---------- Pin map (Table 3.2) ----------
#define PIN_ACS712    34
#define PIN_ZMPT101B  35
#define PIN_DS18B20   4
#define PIN_PIR       13
#define RELAY_LAMP    25
#define RELAY_FAN     26
#define RELAY_PUMP    27
#define RELAY_SPARE   14

#define AC_FREQUENCY  50.0
#define ZERO_V        1.65   // fixed calibration constant

// ---------- Wi-Fi / Firebase ----------
#define WIFI_SSID     "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define API_KEY       "YOUR_FIREBASE_API_KEY"
#define DATABASE_URL  "https://esp32-energy-monitor-9d94d-default-rtdb.asia-southeast1.firebasedatabase.app"

FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// ---------- Sensors ----------
ZMPT101B voltageSensor(PIN_ZMPT101B, AC_FREQUENCY);
ACS712 currentSensor(PIN_ACS712, 3.3, 4095, 100);
OneWire oneWire(PIN_DS18B20);
DallasTemperature tempSensor(&oneWire);
Adafruit_SSD1306 display(128, 64, &Wire, -1);

unsigned long lastUpdate = 0;
unsigned long unoccupiedSince = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(PIN_PIR, INPUT);
  pinMode(RELAY_LAMP, OUTPUT);
  pinMode(RELAY_FAN, OUTPUT);
  pinMode(RELAY_PUMP, OUTPUT);
  pinMode(RELAY_SPARE, OUTPUT);

  tempSensor.begin();
  currentSensor.autoMidPoint(50, 10);

  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();

  Serial.println("Connecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Signal strength (RSSI): ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");

  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;
  Serial.println("Initialising Firebase...");

  if (Firebase.signUp(&config, &auth, "", "")) {
    Serial.println("Firebase signup successful.");
  } else {
    Serial.printf("Firebase signup failed: %s\n", config.signer.signupError.message.c_str());
  }

  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
}

void loop() {
  // --- Sample sensors ---
  float voltage = voltageSensor.getRmsVoltage(10);
  float current_mA = currentSensor.mA_AC_sampling(50, 5);
  float current_A = current_mA / 1000.0;

  tempSensor.requestTemperatures();
  float temp = tempSensor.getTempCByIndex(0);

  bool occupied = digitalRead(PIN_PIR) == HIGH;

  // --- Decision logic (priority: WASTE first, then MAINTENANCE) ---
  String alert = "NONE";

  if (!occupied && current_A > 0.15) {
    alert = "WASTE";
    if (unoccupiedSince == 0) unoccupiedSince = millis();
  } else if (temp > 45.0 && current_A > 0.15) {
    alert = "MAINTENANCE";
    unoccupiedSince = 0;
  } else if (voltage < 200.0 || voltage > 240.0) {
    alert = "SUPPLY_FAULT";
    unoccupiedSince = 0;
  } else {
    unoccupiedSince = 0;
  }

  // --- Relay control based on occupancy ---
  digitalWrite(RELAY_LAMP, occupied ? HIGH : LOW);
  digitalWrite(RELAY_FAN, occupied ? HIGH : LOW);

  // --- OLED update ---
  display.clearDisplay();
  display.setCursor(0, 0);
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.printf("V:%.1fV  I:%.2fA\n", voltage, current_A);
  display.printf("T:%.1fC  Occ:%s\n", temp, occupied ? "YES" : "NO");
  display.printf("Alert: %s\n", alert.c_str());
  display.display();

  // --- Serial output ---
  Serial.println("--------------------------------");
  Serial.printf("Current: %.2fA\n", current_A);
  Serial.printf("Voltage: %.1fV\n", voltage);
  Serial.printf("Temp: %.1fC\n", temp);
  Serial.printf("Occupied: %s\n", occupied ? "YES" : "NO");
  Serial.printf("Alert: %s\n", alert.c_str());
  Serial.printf("RSSI: %d dBm\n", WiFi.RSSI());

  // --- Firebase update ---
  if (Firebase.ready()) {
    FirebaseJson json;
    json.set("current", current_A);
    json.set("voltage", voltage);
    json.set("temp", temp);
    json.set("occupied", occupied);
    json.set("alert", alert);
    json.set("updatedAt", millis());

    if (Firebase.RTDB.setJSON(&fbdo, "/readings", &json)) {
      Serial.println("Firebase update successful.");
    } else {
      Serial.println("Firebase update failed: " + fbdo.errorReason());
    }
  }

  delay(1000);
}