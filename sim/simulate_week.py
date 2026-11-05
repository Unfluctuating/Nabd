"""Simulate one week of minute-level AC load for a 6-unit mosque, with injected
waste and faults (ground truth), so the flag detector can be scored.

Everything here is SIMULATED. Numbers are plausible, not measured:
- unit ratings, compressor cycling, outdoor temperature curve, current model.
Ground the story in the UAE audit study (AlAli et al., Buildings 2023) and
replace with pilot data later.

Usage:  python sim/simulate_week.py [--seed 7]
Writes: data/mosque_week.csv, data/ground_truth.json, data/prayer_windows.csv
"""
import argparse
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

from calendar_dubai import DAYS, WEEK_START, in_window, prayer_events

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

VOLTS, PF = 230.0, 0.9
UNITS = {  # unit id -> rated compressor kW (assumed split/package units)
    1: 2.5, 2: 2.5, 3: 3.0, 4: 3.0, 5: 2.0, 6: 2.0,
}
FAN_KW = 0.15          # indoor fan when unit is on but compressor idle
CYCLE_MIN = 15         # normal compressor cycle period
SHORT_CYCLE_MIN = 4    # faulty cycle period

# Injected ground truth (day index 0 = Mon 9 Nov; 4 = Fri 13 Nov)
GROUND_TRUTH = [
    {"type": "waste", "unit": 3, "day": 1, "from": "Isha_end", "to": "22:30",
     "note": "unit left on after Isha"},
    {"type": "waste", "unit": 3, "day": 4, "from": "Isha_end", "to": "22:30",
     "note": "unit left on after Isha"},
    {"type": "waste", "unit": 1, "day": 5, "from": "Fajr_end", "to": "09:00",
     "note": "unit left on after Fajr"},
    {"type": "high_draw", "unit": 2, "from_day": 3,
     "note": "+25% current (dirty coil / low refrigerant)"},
    {"type": "short_cycling", "unit": 5, "from_day": 2,
     "note": "compressor cycles every ~4 min"},
]


def outdoor_temp(ts, rng):
    """Assumed mid-November Dubai curve: ~22 C at night, ~31 C at 15:00."""
    h = ts.hour + ts.minute / 60
    return 26.5 + 4.5 * math.sin(2 * math.pi * (h - 9) / 24) + rng.gauss(0, 0.3)


def build_waste_spans(events):
    spans = []
    for gt in GROUND_TRUTH:
        if gt["type"] != "waste":
            continue
        day = (WEEK_START + timedelta(days=gt["day"])).isoformat()
        prayer = gt["from"].split("_")[0]
        ev = next(e for e in events if e["day"] == day and e["prayer"] == prayer)
        h, m = map(int, gt["to"].split(":"))
        end = ev["end"].replace(hour=h, minute=m)
        spans.append((gt["unit"], ev["end"], end))
        gt["start"], gt["end"] = ev["end"].isoformat(), end.isoformat()
    return spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--clean", action="store_true",
                    help="no injected waste/faults (control run: expect zero flags)")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    if args.clean:
        GROUND_TRUTH.clear()

    DATA.mkdir(exist_ok=True)
    events = prayer_events()
    waste_spans = build_waste_spans(events)

    # Prayer windows file (what the detector is allowed to know)
    with open(DATA / "prayer_windows.csv", "w") as f:
        f.write("day,prayer,adhan,start,end,units_needed\n")
        for e in events:
            f.write(f"{e['day']},{e['prayer']},{e['adhan'].isoformat()},"
                    f"{e['start'].isoformat()},{e['end'].isoformat()},{e['units_needed']}\n")

    start = datetime(WEEK_START.year, WEEK_START.month, WEEK_START.day)
    rows = []
    for minute in range(DAYS * 24 * 60):
        ts = start + timedelta(minutes=minute)
        day_idx = minute // (24 * 60)
        t_out = outdoor_temp(ts, rng)
        ev = in_window(ts, events)
        needed = ev["units_needed"] if ev else 0

        for unit, kw in UNITS.items():
            called = unit <= needed
            if any(u == unit and s < ts <= e for u, s, e in waste_spans):
                called = True

            power = 0.0
            if called:
                duty = min(0.95, max(0.3, 0.4 + 0.04 * (t_out - 25)))
                period = CYCLE_MIN
                if unit == 5 and day_idx >= 2 and not args.clean:
                    period = SHORT_CYCLE_MIN
                    duty = 0.5
                phase = (minute + unit * 3) % period
                comp_on = phase < duty * period
                power = FAN_KW
                if comp_on:
                    load = kw * (1 + 0.01 * (t_out - 25))   # draw rises with ambient
                    if unit == 2 and day_idx >= 3 and not args.clean:
                        load *= 1.25
                    power += load
                power *= 1 + rng.gauss(0, 0.03)
            current = power * 1000 / (VOLTS * PF)
            rows.append((ts.isoformat(), unit, round(current, 2), round(power, 3),
                         round(t_out, 2)))

    with open(DATA / "mosque_week.csv", "w") as f:
        f.write("timestamp,unit,current_a,power_kw,outdoor_c\n")
        for r in rows:
            f.write(",".join(map(str, r)) + "\n")

    with open(DATA / "ground_truth.json", "w") as f:
        json.dump(GROUND_TRUTH, f, indent=2)

    print(f"Wrote {len(rows):,} rows ({DAYS} days x {len(UNITS)} units x 1440 min) "
          f"to {DATA / 'mosque_week.csv'}")
    print(f"Injected {len(GROUND_TRUTH)} ground-truth events -> {DATA / 'ground_truth.json'}")


if __name__ == "__main__":
    main()
