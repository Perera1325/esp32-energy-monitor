// Test Case 4: PIR Motion Sensor + Fan (Relay) + OLED Display Test

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define PIR_PIN     13
#define RELAY_FAN   26
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

int waveformBuffer[SCREEN_WIDTH];
int waveIndex = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(PIR_PIN, INPUT);
  pinMode(RELAY_FAN, OUTPUT);
  digitalWrite(RELAY_FAN, LOW);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed");
  }
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  Serial.println();
  Serial.println("   PIR + FAN (RELAY) + OLED TEST");
  Serial.println("Warming up PIR sensor...");
  delay(2000);
  Serial.println("PIR ready.");
  Serial.println();
}

void loop() {
  int motionState = digitalRead(PIR_PIN);

  if (motionState == HIGH) {
    digitalWrite(RELAY_FAN, HIGH);
    Serial.println("Motion Detected! Fan ON");
  } else {
    digitalWrite(RELAY_FAN, LOW);
    Serial.println("No motion detected. Fan OFF");
  }

  // Update waveform buffer with current PIR state
  waveformBuffer[waveIndex] = motionState ? 20 : 0;
  waveIndex = (waveIndex + 1) % SCREEN_WIDTH;

  // Draw live waveform on OLED
  display.clearDisplay();
  display.setCursor(0, 0);
  display.print("PIR: ");
  display.println(motionState ? "MOTION" : "CLEAR");
  display.print("Fan: ");
  display.println(motionState ? "ON" : "OFF");

  for (int x = 0; x < SCREEN_WIDTH - 1; x++) {
    int idx1 = (waveIndex + x) % SCREEN_WIDTH;
    int idx2 = (waveIndex + x + 1) % SCREEN_WIDTH;
    display.drawLine(x, 40 - waveformBuffer[idx1],
                      x + 1, 40 - waveformBuffer[idx2], SSD1306_WHITE);
  }
  display.display();

  delay(500);
}