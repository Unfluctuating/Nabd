"""Detect waste and faults in a mosque AC load file, write flags + a technician
digest, and score against the simulator's ground truth (if present).

The detector only uses the load data and the prayer-window calendar - never
the ground truth - so the score is a fair check of the logic on SIMULATED data.

Usage:  python sim/flags.py [--tariff 0.40] [--grace 10]
Reads:  data/mosque_week.csv, data/prayer_windows.csv, (data/ground_truth.json)
Writes: data/flags.json
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

ON_KW = 0.10          # unit drawing anything (fan or compressor)
COMP_KW = 0.60        # compressor running
WASTE_MIN = 30        # minutes outside prayer windows before we call it waste
SHORT_STARTS_PER_H = 8
SHORT_MEDIAN_RUN = 5  # minutes
HIGH_DRAW_RATIO = 1.12
BASELINE_DAYS = 2     # learning period assumed clean


def runs(mask):
    """Yield (start_idx, end_idx_inclusive) for consecutive True values."""
    idx = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(int), [0]))))
    for s, e in zip(idx[::2], idx[1::2]):
        yield s, e - 1


def window_mask(ts, windows, grace):
    m = np.zeros(len(ts), dtype=bool)
    g = pd.Timedelta(minutes=grace)
    for _, w in windows.iterrows():
        m |= (ts >= w["start"] - g) & (ts <= w["end"] + g)
    return m


def detect(df, windows, tariff, grace):
    flags = []
    df = df.sort_values(["unit", "timestamp"])
    day0 = df["timestamp"].min().normalize()

    for unit, u in df.groupby("unit"):
        u = u.reset_index(drop=True)
        ts = u["timestamp"]
        drawing = (u["power_kw"] > ON_KW).to_numpy()
        inwin = window_mask(ts, windows, grace)

        # 1) Waste: drawing power outside any prayer window for >= WASTE_MIN
        for s, e in runs(drawing & ~inwin):
            dur = e - s + 1
            if dur >= WASTE_MIN:
                kwh = u.loc[s:e, "power_kw"].sum() / 60
                before = windows[windows["end"] <= ts[s]]
                after_prayer = before.iloc[-1]["prayer"] if len(before) else "midnight"
                flags.append({
                    "type": "waste", "unit": int(unit), "severity": "medium",
                    "start": ts[s].isoformat(), "end": ts[e].isoformat(),
                    "kwh": round(kwh, 2), "aed": round(kwh * tariff, 2),
                    "reason": f"Unit {unit} ran {dur} min after {after_prayer} on "
                              f"{ts[s]:%a %d %b} ({ts[s]:%H:%M}-{ts[e]:%H:%M}), outside any "
                              "prayer window.",
                })

        comp = (u["power_kw"] > COMP_KW).to_numpy()
        u["day"] = ((ts - day0).dt.days).astype(int)

        # 2) Short-cycling: many compressor starts per hour of use, short runs
        short_days = []
        for day, d in u.groupby("day"):
            c = (d["power_kw"] > COMP_KW).to_numpy()
            used_h = (d["power_kw"] > ON_KW).sum() / 60
            run_lens = [e - s + 1 for s, e in runs(c)]
            if used_h < 0.5 or not run_lens:
                continue
            starts_per_h = len(run_lens) / used_h
            if starts_per_h > SHORT_STARTS_PER_H and np.median(run_lens) < SHORT_MEDIAN_RUN:
                short_days.append((int(day), round(starts_per_h, 1), float(np.median(run_lens))))
        if short_days:
            first = short_days[0]
            flags.append({
                "type": "short_cycling", "unit": int(unit), "severity": "high",
                "from_day": first[0], "days_flagged": [d for d, _, _ in short_days],
                "reason": f"Unit {unit} compressor started ~{first[1]} times per hour of use "
                          f"with ~{first[2]:.0f}-min runs (normal here: ~4/h, 6+ min). "
                          "Check thermostat placement, refrigerant charge, contactor.",
            })

        # 3) High draw: compressor power above this unit's own baseline at the same outdoor temp
        on = u[comp]
        base = on[on["day"] < BASELINE_DAYS]
        if len(base) >= 60:
            slope, intercept = np.polyfit(base["outdoor_c"], base["power_kw"], 1)
            high_days = []
            for day, d in on[on["day"] >= BASELINE_DAYS].groupby("day"):
                pred = slope * d["outdoor_c"] + intercept
                ratio = float(np.median(d["power_kw"] / pred))
                if ratio > HIGH_DRAW_RATIO:
                    high_days.append((int(day), ratio))
            if high_days:
                flags.append({
                    "type": "high_draw", "unit": int(unit), "severity": "high",
                    "from_day": high_days[0][0], "days_flagged": [d for d, _ in high_days],
                    "reason": f"Unit {unit} draws ~{(high_days[0][1] - 1) * 100:.0f}% more than its "
                              "own normal at the same outdoor temperature. Likely dirty coil or "
                              "low refrigerant - schedule a service visit.",
                })
    return flags


def score(flags, truth):
    def match(f, t):
        if f["type"] != t["type"] or f["unit"] != t["unit"]:
            return False
        if t["type"] == "waste":
            return f["start"] < t["end"] and f["end"] > t["start"]
        return True

    tp_truth = sum(any(match(f, t) for f in flags) for t in truth)
    tp_flags = sum(any(match(f, t) for t in truth) for f in flags)
    precision = tp_flags / len(flags) if flags else 0.0
    recall = tp_truth / len(truth) if truth else 0.0
    return precision, recall, tp_flags, len(flags), tp_truth, len(truth)


def digest(flags):
    order = {"high": 0, "medium": 1}
    ranked = sorted(flags, key=lambda f: (order[f["severity"]], -f.get("aed", 0)))
    lines = ["Technician digest - Mosque A (SIMULATED DATA)", ""]
    for i, f in enumerate(ranked, 1):
        cost = f"  ~{f['kwh']} kWh, ~AED {f['aed']}" if "kwh" in f else ""
        lines.append(f"{i}. [{f['severity'].upper()}] {f['type']}: {f['reason']}{cost}")
        lines.append("   -> Confirm / False alarm")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tariff", type=float, default=0.40,
                    help="AED per kWh (ASSUMPTION - replace with the real tariff)")
    ap.add_argument("--grace", type=int, default=10, help="minutes of grace around windows")
    args = ap.parse_args()

    df = pd.read_csv(DATA / "mosque_week.csv", parse_dates=["timestamp"])
    windows = pd.read_csv(DATA / "prayer_windows.csv", parse_dates=["start", "end"])
    flags = detect(df, windows, args.tariff, args.grace)

    with open(DATA / "flags.json", "w") as f:
        json.dump(flags, f, indent=2)
    print(digest(flags))

    gt_path = DATA / "ground_truth.json"
    if gt_path.exists():
        truth = json.loads(gt_path.read_text())
        p, r, tpf, nf, tpt, nt = score(flags, truth)
        print(f"\nScore vs simulated ground truth: precision {p:.0%} ({tpf}/{nf} flags correct), "
              f"recall {r:.0%} ({tpt}/{nt} injected events found)")


if __name__ == "__main__":
    main()
