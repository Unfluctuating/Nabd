/*
  Nabd demo rig — ESP32-S3 + INA219 + logic-level MOSFET + 12 V brushed gearmotor
  STATUS: written for the demo, NOT yet compiled or bench-tested. Calibrate thresholds first.

  Library: Adafruit INA219 (Arduino Library Manager)
  Board:   ESP32-S3 Dev Module (Arduino-ESP32 core)

  Serial commands (115200 baud):
    a = auto thermostat cycle (normal)   s = short-cycle (fault)
    o = always on                        x = off
  Output: one JSON line every 100 ms, e.g.
    {"t":12345,"ma":412.3,"peak":980.1,"v":11.92,"on":1,"starts60":3,"mode":"auto","flag":"NONE"}
*/
#include <Wire.h>
#include <Adafruit_INA219.h>

// ---- Pins (check your board's pinout) ----
const int PIN_SDA  = 8;
const int PIN_SCL  = 9;
const int PIN_GATE = 10;

// ---- Thresholds: CALIBRATE ON THE BENCH (hardware/README.md) ----
float OFF_MA   = 30.0;    // below = motor not drawing current
float STALL_MA = 900.0;   // window mean above this = stalled (set between run and stall current)
const uint32_t STALL_MS          = 1500;  // stalled this long -> LOCKED_ROTOR
const uint32_t STALL_CUTOFF_MS   = 3000;  // demo-rig protection: cut motor after this
const uint32_t STALL_REST_MS     = 5000;  // ...and rest this long before retrying
const int      SHORT_CYCLE_STARTS = 6;    // starts in the last 60 s (demo-scaled)

// ---- Demo-scaled thermostat timings ----
const uint32_t AUTO_ON_MS = 8000, AUTO_OFF_MS = 8000;
const uint32_t SHORT_ON_MS = 1500, SHORT_OFF_MS = 1500;

Adafruit_INA219 ina219;

enum Mode { MODE_AUTO, MODE_SHORT, MODE_ON, MODE_OFF };
Mode mode = MODE_AUTO;

bool gateOn = false;
uint32_t phaseStart = 0;

// sampling window
const uint32_t SAMPLE_US = 2000;   // ~500 Hz
const uint32_t WINDOW_MS = 100;
uint32_t lastSampleUs = 0, windowStart = 0;
double sumMa = 0; float peakMa = 0; uint32_t nSamples = 0;

// state
bool drawing = false;
uint32_t stallSince = 0;
bool cutoff = false; uint32_t cutoffSince = 0;
const int MAX_STARTS = 64;
uint32_t startTimes[MAX_STARTS]; int startHead = 0, startCount = 0;

const char* modeName() {
  switch (mode) {
    case MODE_AUTO: return "auto";
    case MODE_SHORT: return "short";
    case MODE_ON: return "on";
    default: return "off";
  }
}

void setGate(bool on) {
  gateOn = on;
  digitalWrite(PIN_GATE, on ? HIGH : LOW);
}

void recordStart(uint32_t now) {
  startTimes[startHead] = now;
  startHead = (startHead + 1) % MAX_STARTS;
  if (startCount < MAX_STARTS) startCount++;
}

int startsInLast60s(uint32_t now) {
  int n = 0;
  for (int i = 0; i < startCount; i++) {
    if (now - startTimes[i] <= 60000UL) n++;
  }
  return n;
}

void handleSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    Mode prev = mode;
    if (c == 'a') mode = MODE_AUTO;
    else if (c == 's') mode = MODE_SHORT;
    else if (c == 'o') mode = MODE_ON;
    else if (c == 'x') mode = MODE_OFF;
    if (mode != prev) { phaseStart = millis(); setGate(mode != MODE_OFF); }
  }
}

void updateThermostat(uint32_t now) {
  if (cutoff) {                       // demo protection after a stall
    if (now - cutoffSince >= STALL_REST_MS) { cutoff = false; phaseStart = now; }
    else { setGate(false); return; }
  }
  uint32_t onMs = 0, offMs = 0;
  if (mode == MODE_AUTO)  { onMs = AUTO_ON_MS;  offMs = AUTO_OFF_MS; }
  if (mode == MODE_SHORT) { onMs = SHORT_ON_MS; offMs = SHORT_OFF_MS; }
  if (mode == MODE_ON)  { setGate(true);  return; }
  if (mode == MODE_OFF) { setGate(false); return; }
  uint32_t elapsed = now - phaseStart;
  if (gateOn && elapsed >= onMs)   { setGate(false); phaseStart = now; }
  if (!gateOn && elapsed >= offMs) { setGate(true);  phaseStart = now; }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_GATE, OUTPUT);
  setGate(false);
  Wire.begin(PIN_SDA, PIN_SCL);
  if (!ina219.begin()) {
    Serial.println("{\"error\":\"INA219 not found - check SDA/SCL wiring and 3V3\"}");
    while (true) delay(1000);
  }
  ina219.setCalibration_32V_2A();   // covers the stall current of a small 12 V motor
  phaseStart = windowStart = millis();
  setGate(true);
}

void loop() {
  uint32_t now = millis();
  handleSerial();
  updateThermostat(now);

  uint32_t us = micros();
  if (us - lastSampleUs >= SAMPLE_US) {
    lastSampleUs = us;
    float ma = ina219.getCurrent_mA();
    if (ma < 0) ma = 0;              // ignore small negative offsets
    sumMa += ma; nSamples++;
    if (ma > peakMa) peakMa = ma;
  }

  if (now - windowStart >= WINDOW_MS && nSamples > 0) {
    float meanMa = sumMa / nSamples;
    float busV = ina219.getBusVoltage_V();

    // start detection: off -> drawing transition
    bool nowDrawing = meanMa > OFF_MA;
    if (nowDrawing && !drawing) recordStart(now);
    drawing = nowDrawing;

    // stall detection
    const char* flag = "NONE";
    if (meanMa > STALL_MA) {
      if (stallSince == 0) stallSince = now;
      if (now - stallSince >= STALL_MS) flag = "LOCKED_ROTOR";
      if (now - stallSince >= STALL_CUTOFF_MS && !cutoff) {
        cutoff = true; cutoffSince = now; setGate(false);
      }
    } else {
      stallSince = 0;
    }

    int starts = startsInLast60s(now);
    if (strcmp(flag, "NONE") == 0 && starts >= SHORT_CYCLE_STARTS) flag = "SHORT_CYCLING";

    Serial.printf("{\"t\":%lu,\"ma\":%.1f,\"peak\":%.1f,\"v\":%.2f,\"on\":%d,\"starts60\":%d,\"mode\":\"%s\",\"flag\":\"%s\"}\n",
                  (unsigned long)now, meanMa, peakMa, busV, gateOn ? 1 : 0, starts, modeName(), flag);

    sumMa = 0; peakMa = 0; nSamples = 0; windowStart = now;
  }
}
