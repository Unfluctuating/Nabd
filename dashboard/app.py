"""Nabd dashboard - Streamlit viewer for the simulated mosque week.

Run from the repo root after the simulator and detector:
    python sim/simulate_week.py && python sim/flags.py
    streamlit run dashboard/app.py
"""
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data"

st.set_page_config(page_title="Nabd - Mosque AC monitor", layout="wide")
st.title("Nabd · Mosque AC monitor")
st.caption("SIMULATED DATA — one 6-unit mosque, Dubai, 9–15 Nov 2026. Prayer times approximate.")

if not (DATA / "flags.json").exists():
    st.error("No data yet. Run `python sim/simulate_week.py` then `python sim/flags.py`.")
    st.stop()


@st.cache_data
def load():
    df = pd.read_csv(DATA / "mosque_week.csv", parse_dates=["timestamp"])
    win = pd.read_csv(DATA / "prayer_windows.csv", parse_dates=["adhan", "start", "end"])
    flags = json.loads((DATA / "flags.json").read_text())
    return df, win, flags


df, win, flags = load()
days = sorted(df["timestamp"].dt.date.unique())

# ---- Digest ----
st.subheader("Technician digest — visit these first")
order = {"high": 0, "medium": 1}
ranked = sorted(flags, key=lambda f: (order[f["severity"]], -f.get("aed", 0)))
for i, f in enumerate(ranked, 1):
    cost = f" · ~{f['kwh']} kWh · ~AED {f['aed']}" if "kwh" in f else ""
    icon = "🔴" if f["severity"] == "high" else "🟠"
    c1, c2 = st.columns([8, 2])
    c1.markdown(f"{icon} **{i}. {f['type'].replace('_', ' ')} — Unit {f['unit']}**  \n{f['reason']}{cost}")
    c2.radio("Technician", ["—", "Confirm", "False alarm"], key=f"fb{i}",
             horizontal=False, label_visibility="collapsed")

# ---- Timeline ----
st.subheader("Load vs prayer windows")
c1, c2 = st.columns(2)
day = c1.selectbox("Day", days, format_func=lambda d: d.strftime("%a %d %b"))
units = c2.multiselect("Units", sorted(df["unit"].unique()), default=sorted(df["unit"].unique()))

d = df[(df["timestamp"].dt.date == day) & (df["unit"].isin(units))]
w = win[win["start"].dt.date == day]

bands = alt.Chart(w).mark_rect(opacity=0.15, color="#2a9d8f").encode(
    x="start:T", x2="end:T", tooltip=["prayer", "adhan:T"])
labels = alt.Chart(w).mark_text(dy=-6, color="#2a9d8f", fontSize=11).encode(
    x="adhan:T", y=alt.value(0), text="prayer")
lines = alt.Chart(d).mark_line(strokeWidth=1).encode(
    x=alt.X("timestamp:T", title="Time"),
    y=alt.Y("power_kw:Q", title="kW"),
    color=alt.Color("unit:N", title="Unit"),
    tooltip=["timestamp:T", "unit:N", "power_kw:Q", "outdoor_c:Q"])
st.altair_chart((bands + labels + lines).properties(height=360), width="stretch")

st.caption("Green bands = prayer windows (when cooling is legitimate). "
           "Load outside them for 30+ min is flagged as waste.")
