"""Worship calendar for the simulated mosque week (Dubai, 9-15 Nov 2026).

ASSUMPTIONS - replace before relying on any number:
- Prayer times are APPROXIMATE Dubai times for mid-November, held constant
  across the week. Replace with the official Awqaf timetable.
- UAE Friday prayer (Jumu'ah) is assumed at 13:15 (unified time since 2022);
  confirm before the pitch.
- Occupancy windows (minutes before/after the call to prayer) are guesses;
  the pilot would learn them per mosque from technician feedback.
"""
from datetime import date, datetime, timedelta

WEEK_START = date(2026, 11, 9)  # Monday
DAYS = 7

# Approximate Dubai prayer times, mid-November (HH:MM)
PRAYERS = {
    "Fajr": "05:13",
    "Dhuhr": "11:58",
    "Asr": "15:08",
    "Maghrib": "17:34",
    "Isha": "18:49",
}
JUMUAH = "13:15"

# (minutes before adhan, minutes after adhan, number of AC units needed)
WINDOWS = {
    "Fajr": (20, 40, 2),
    "Dhuhr": (20, 40, 3),
    "Asr": (20, 35, 3),
    "Maghrib": (15, 30, 5),
    "Isha": (20, 45, 5),
    "Jumuah": (60, 60, 6),
}


def _at(d, hhmm):
    h, m = map(int, hhmm.split(":"))
    return datetime(d.year, d.month, d.day, h, m)


def prayer_events():
    """List of dicts: day, prayer, adhan, start, end, units_needed."""
    events = []
    for i in range(DAYS):
        d = WEEK_START + timedelta(days=i)
        is_friday = d.weekday() == 4
        for name, hhmm in PRAYERS.items():
            label, t = name, hhmm
            if is_friday and name == "Dhuhr":
                label, t = "Jumuah", JUMUAH
            before, after, units = WINDOWS[label]
            adhan = _at(d, t)
            events.append({
                "day": d.isoformat(),
                "prayer": label,
                "adhan": adhan,
                "start": adhan - timedelta(minutes=before),
                "end": adhan + timedelta(minutes=after),
                "units_needed": units,
            })
    return events


def in_window(ts, events, grace_min=0):
    """Return the event covering timestamp ts (with optional grace), else None."""
    g = timedelta(minutes=grace_min)
    for e in events:
        if e["start"] - g <= ts <= e["end"] + g:
            return e
    return None
