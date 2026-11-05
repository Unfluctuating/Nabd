# Nabd (نبض — "pulse")

Team Jalpari — UAE Hackathon 2026, Dubai round (9–11 Nov, HCT Dubai, Pioneers)
Theme: Responsible AI & Smart Cognitive Government
Challenge: **#36 GAIAEZ — Intelligent Mosque Operations for Resource Efficiency and Sustainability**
Profile: https://drive.google.com/file/d/196QOtDorcwimEZlIMqfk7AQpIgFCjKQc/view

> ⚠️ We are currently registered under MOCCAE #35 (Sijil). Using this repo needs the organisers to confirm we can switch challenge.

## The idea in one line

A clip-on sensor kit for each mosque that learns every AC unit's electrical "heartbeat", compares it with the mosque's prayer calendar, and tells technicians each morning which mosques are wasting power and which units are about to fail — diagnosis and advice only, it never switches anything off.

## Problem

HVAC is the biggest energy load in UAE mosques, and AC often runs far beyond prayer times. A study of 146 audited UAE mosques found a mean of 123.4 kWh/m² before audits and 84 kWh/m² after ([AlAli et al., *Buildings* 2023](https://www2.mdpi.com/2075-5309/13/4/1007)). Big programmes exist (Siemens/Etihad ESCO, ADDC smart thermostats — see `docs/prior-work.md`), but they *control* setpoints. Nobody can cheaply answer: *is this load legitimate demand, waste, or a failing unit?* That is the challenge's root cause **R4**, almost word for word.

## What we build

1. **Clip-on sensing** — ESP32-S3 + current sensor per AC circuit + room temperature. No BMS, no rewiring, **no cameras** in the prayer hall.
2. **Worship-calendar baseline** — expected load from the 5 prayer times, Jumu'ah, Ramadan, Eid and outdoor temperature.
3. **Two kinds of flags**
   - *Waste:* "Unit 3 ran 95 min after Isha, outside Ramadan — ~6 kWh."
   - *Fault:* short-cycling, high draw vs the unit's own normal, locked rotor / failed start.
4. **Technician digest** — a ranked "visit these first" list in Arabic and English, each flag with its reason and estimated AED; technician taps Confirm / False alarm (labels improve the model).

## Responsible AI

- Advisory only: no automatic switching, so worshipper comfort and safety stay with humans (profile R5)
- Every flag shows why it fired
- No cameras, no personal data — only electrical current and temperature
- Real installs on 230/400 V boards are done only by licensed electricians

## 3-day demo plan

- **Live rig (12 V only):** a 12 V brushed motor driven by the ESP32 on a schedule → hold the shaft = locked-rotor flag; toggle fast = short-cycling flag.
- **Replay:** a simulated mosque week (`sim/`) with prayer windows → waste and fault flags → digest.
- Data shown as **simulated** on every slide.

## Repo layout

| Path | What |
|---|---|
| `docs/` | challenge summary, prior work, 3-min pitch, 90-day plan, BMC |
| `hardware/` | demo BOM and wiring (with safety notes) |
| `firmware/nabd_demo/` | ESP32-S3 + INA219 sketch (**not yet compiled or bench-tested**) |
| `sim/` | mosque-week simulator + flag detector (**tested in Python**) |
| `dashboard/` | Streamlit viewer for the simulated week |

Quick start:

```bash
pip install -r requirements.txt
python sim/simulate_week.py      # writes data/mosque_week.csv + data/ground_truth.json
python sim/flags.py              # writes data/flags.json, prints digest + precision/recall
streamlit run dashboard/app.py
```

## Deliverables (Pioneers)

- Idea + Business Model Canvas (BMC is one slide of the deck)
- 3-minute pitch + 2 minutes Q&A; submit by **10:00, 11 Nov**
- Demo (optional, but it's what wins)

## Team

| Name | Role |
|---|---|
| Melvin Jacob Sajan | Lead, pitch |
| Mohammad Adnan Khan | Hardware + firmware |
| Aaron Thomas George | TBD |
| Bejoy Sajith | TBD |
| Gloria Padamati | TBD |
| Ruhaan Pramesh Nair | TBD |
| Dhruv Madhu | TBD |

Suggested open roles: simulator/model · dashboard · LLM digest + data sourcing · BMC/market/90-day plan · deck + Q&A prep.

## Open questions

- Can we switch from #35 to #36? (email admin@hackathon.ae)
- Who pays a mosque's electricity bill — the mosque, GAIAEZ/Awqaf, or the utility? Decides the buyer.
- Can we pull the official Awqaf prayer timetable, or must we calculate times?
- Bayanat: any mosque or building-energy datasets?
