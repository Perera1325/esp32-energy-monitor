// Test Case 3: PIR Motion Sensor + LED Indicator Test
// sketch_sep22c.ino

#define PIR_PIN 13
#define LED_PIN 2   // onboard/external LED — confirm actual pin used

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(PIR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);

  Serial.println();
  Serial.println("   PIR MOTION SENSOR TEST");
  Serial.println("Warming up PIR sensor...");
  delay(2000);
  Serial.println("PIR ready.");
  Serial.println();
}

void loop() {
  int motionState = digitalRead(PIR_PIN);

  if (motionState == HIGH) {
    digitalWrite(LED_PIN, HIGH);
    Serial.println("Motion Detected!");
  } else {
    digitalWrite(LED_PIN, LOW);
    Serial.println("No motion detected.");
  }

  delay(1000);
}