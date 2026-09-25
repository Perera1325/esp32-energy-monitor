// Test Case 5: PIR Motion Sensor + Fan + LED (Two Relay Channels) + OLED Display Test

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define PIR_PIN     13
#define RELAY_LAMP  25
#define RELAY_FAN   26
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(PIR_PIN, INPUT);
  pinMode(RELAY_LAMP, OUTPUT);
  pinMode(RELAY_FAN, OUTPUT);
  digitalWrite(RELAY_LAMP, LOW);
  digitalWrite(RELAY_FAN, LOW);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed");
  }
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  Serial.println();
  Serial.println("   PIR + FAN + LED (DUAL RELAY) + OLED TEST");
  Serial.println("Warming up PIR sensor...");
  delay(2000);
  Serial.println("PIR ready.");
  Serial.println();
}

void loop() {
  int motionState = digitalRead(PIR_PIN);

  if (motionState == HIGH) {
    digitalWrite(RELAY_LAMP, HIGH);
    digitalWrite(RELAY_FAN, HIGH);
    Serial.println("Motion Detected! Lamp ON, Fan ON");
  } else {
    digitalWrite(RELAY_LAMP, LOW);
    digitalWrite(RELAY_FAN, LOW);
    Serial.println("No motion detected. Lamp OFF, Fan OFF");
  }

  // Update OLED status
  display.clearDisplay();
  display.setCursor(0, 0);
  display.print("PIR: ");
  display.println(motionState ? "MOTION" : "CLEAR");
  display.print("Lamp: ");
  display.println(motionState ? "ON" : "OFF");
  display.print("Fan: ");
  display.println(motionState ? "ON" : "OFF");
  display.display();

  delay(500);
}
