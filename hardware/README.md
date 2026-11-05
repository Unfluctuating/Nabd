# Demo hardware (12 V only — no mains in the venue)

The demo rig stands in for one mosque AC unit: a 12 V brushed gearmotor is the "compressor", the ESP32 switches it like a thermostat, and an INA219 measures its current.

## BOM (prices are estimates — not checked; Amazon.ae / Noon / Deira shops)

| Qty | Part | Why this one | ~AED |
|---|---|---|---|
| 1 | ESP32-S3 dev board (DevKitC-1 or similar) | Sampling, features, USB serial | 45–70 |
| 1 | INA219 breakout (0.1 Ω shunt) | 3.3 V logic, I²C, high-side current + bus voltage | 15–25 |
| 1 | 12 V brushed DC gearmotor with a wheel/disc, **stall current < 2 A** (N20 or JGA25-370 class) | Brushed motors draw *more* current when stalled → clear fault signature. Avoid brushless PC fans: their stall protection cuts current, which confuses the demo | 20–40 |
| 1 | Logic-level N-MOSFET breakout with R<sub>DS(on)</sub> rated at V<sub>GS</sub> ≤ 3.3 V (e.g. AO3400A, or a D4184/LR7843 module) | ESP32 gate drive is 3.3 V. **Do not use the common IRF520 module** — it isn't fully on at 3.3 V | 10–15 |
| 1 | Schottky diode 1N5819 (or 1N4007) | Flyback across the motor | 2 |
| 1 | 2 A fuse + holder (or polyfuse) | Protects INA219 (3.2 A max with 0.1 Ω) and wiring | 5–10 |
| 1 | 100 Ω + 10 kΩ resistors | Gate series + gate pull-down | 1 |
| 1 | SHT31 or DHT22 | Room temperature (optional for demo) | 20–40 |
| 1 | 12 V 2 A DC adapter + DC barrel jack | Motor supply | 25–35 |
| — | Breadboard, jumpers | | 15–20 |
| | **Total** | | **~160–260** |

## Wiring

```
12V+ ──[2 A fuse]── INA219 VIN+ 
                    INA219 VIN- ──┬── Motor (+)
                                  │
                           1N5819 cathode (stripe) at Motor (+)
                           1N5819 anode at Motor (−)
                                  │
                    Motor (−) ────┴── MOSFET Drain
                                      MOSFET Source ── GND (common)
ESP32 GPIO10 ──[100 Ω]── MOSFET Gate ──[10 kΩ]── GND

INA219 VCC ── ESP32 3V3     INA219 GND ── GND (common)
INA219 SDA ── ESP32 GPIO8   INA219 SCL ── ESP32 GPIO9
ESP32 powered + data over USB from the laptop
```

GPIO8/9/10 are typical for ESP32-S3 DevKitC Arduino builds — **check your board's pinout** and change the pin constants in the sketch if needed.

## Safety checklist
- [ ] **Shared ground**: 12 V supply GND, ESP32 GND, INA219 GND and MOSFET source all tied together
- [ ] **Flyback diode** across the motor, stripe toward +12 V — without it the switching spike can kill the MOSFET
- [ ] Motor stall current < 2 A (check the motor's listing/datasheet), fuse fitted
- [ ] Never power the ESP32 from 12 V directly (use USB, or a buck converter to 5 V)
- [ ] Hold the **wheel**, not the shaft or gears, to stall it; keep fingers away from the gearbox
- [ ] No mains anywhere in the demo. Real installs (split-core CT clamps such as SCT-013 on 230/400 V AC circuits) are done only by a licensed electrician

## Where to confirm specs
- INA219 (TI SBOS448): *Absolute Maximum Ratings* (bus voltage 26 V) and the PGA / shunt range section (±320 mV → ±3.2 A with 0.1 Ω)
- MOSFET: *Electrical Characteristics* → R<sub>DS(on)</sub> at V<sub>GS</sub> = 2.5 V or 3.3 V
- Motor: stall current at 12 V

## Bench checks before the event
1. Motor running normally: note steady current (mA) → set `RUN_MIN_MA` in the sketch below it
2. Wheel held for 3 s: note stall current → set `STALL_MA` between run and stall
3. Send `s` (short-cycle mode): confirm the sketch counts starts and raises `SHORT_CYCLING`
