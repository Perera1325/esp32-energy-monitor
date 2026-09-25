#include <ZMPT101B.h>
#include <ACS712.h>

#define ZMPT_PIN 35
#define ACS_PIN  34
#define AC_FREQUENCY 50.0

// ZMPT101B
ZMPT101B voltageSensor(ZMPT_PIN, AC_FREQUENCY);

// ACS712-20A = 100 mV/A
ACS712 currentSensor(ACS_PIN, 3.3, 4095, 100);

void setup() {
  Serial.begin(115200);
  delay(1000);

  analogReadResolution(12);
  analogSetPinAttenuation(ZMPT_PIN, ADC_11db);
  analogSetPinAttenuation(ACS_PIN, ADC_11db);

  Serial.println();
  Serial.println("   12V AC VOLTAGE + CURRENT");
  Serial.println("Calibrating ACS712...");
  Serial.println("REMOVE LOAD / ZERO CURRENT");

  delay(3000);

  currentSensor.autoMidPoint(50, 20);
  Serial.println("ACS712 calibration complete.");
  Serial.println();
}

void loop() {

  // VOLTAGE
  float voltage = voltageSensor.getRmsVoltage(10);

  // CURRENT
  float current_mA =
      currentSensor.mA_AC_sampling(50, 10);

  float current_A = current_mA / 1000.0;
  Serial.println("--------------------------------");
  Serial.print("Voltage : ");
  Serial.print(voltage, 2);
  Serial.println(" V RMS");
  Serial.print("Current : ");
  Serial.print(current_mA, 1);
  Serial.println(" mA RMS");
  Serial.print("Current : ");
  Serial.print(current_A, 3);
  Serial.println(" A RMS");
  Serial.println("--------------------------------");

  delay(1000);
}