import os
import time
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="CrowdFlow — Step 2 (with Prediction)", layout="wide")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "crowd_stream.csv")

st.title("🧭 CrowdFlow — Real-Time Smart Crowd Flow (Step 2: Prediction)")
st.caption("Now includes EWMA-based forecasting (multi-step lookahead).")

# Sidebar controls
st.sidebar.header("Controls")
cap_a = st.sidebar.number_input("Gate A Capacity", min_value=50, max_value=2000, value=300, step=10)
cap_b = st.sidebar.number_input("Gate B Capacity", min_value=50, max_value=2000, value=280, step=10)
cap_c = st.sidebar.number_input("Gate C Capacity", min_value=50, max_value=2000, value=260, step=10)
cap_d = st.sidebar.number_input("Gate D Capacity", min_value=50, max_value=2000, value=240, step=10)
threshold = st.sidebar.slider("Alert Threshold (% of capacity)", 0.4, 1.0, 0.8, 0.05)
ewma_alpha = st.sidebar.slider("Prediction EWMA Alpha", 0.05, 0.9, 0.3, 0.05)
forecast_horizon = st.sidebar.slider("Forecast Horizon (steps)", 1, 10, 5, 1)
refresh_secs = st.sidebar.slider("Refresh every (seconds)", 0.5, 5.0, 1.0, 0.5)
run_seconds = st.sidebar.slider("Run duration (seconds)", 10, 1200, 300, 10)

capacities = {"Gate A": cap_a, "Gate B": cap_b, "Gate C": cap_c, "Gate D": cap_d}

# --- Helpers ---
def load_data():
    if not os.path.exists(CSV_PATH):
        return None
    try:
        df = pd.read_csv(CSV_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])
        df = df.sort_values("timestamp")
        return df
    except Exception as e:
        st.warning(f"Waiting for stream... ({e})")
        return None

def latest_counts(df):
    latest = df.groupby("zone").tail(1).set_index("zone")["count"].to_dict()
    for z in ["Gate A","Gate B","Gate C","Gate D"]:
        latest.setdefault(z, 0)
    return latest

def ewma_forecast(series, alpha=0.3, horizon=5):
    """multi-step EWMA forecast"""
    if len(series) == 0:
        return [0]*horizon
    last = series.iloc[-1]
    forecast = []
    for _ in range(horizon):
        last = alpha*last + (1-alpha)*series.mean()
        forecast.append(last)
    return forecast

# --- UI ---
start_btn = st.button("▶ Start Live View")

if start_btn:
    ph = st.empty()
    start = time.time()
    while time.time() - start < run_seconds:
        df = load_data()
        if df is not None and not df.empty:
            latest = latest_counts(df)
            # KPIs
            cols = st.columns(4)
            for i,(g,c) in enumerate(latest.items()):
                cols[i].metric(g, c, f"/ {capacities[g]}")
            # Alerts
            alerts = []
            for g,c in latest.items():
                if c >= capacities[g]*threshold:
                    alerts.append(f"🚨 {g} congested ({c}/{capacities[g]}) → reroute")
            if alerts:
                st.error("\n".join(alerts))
            else:
                st.success("✅ Flow normal")


            # --- AI Routing Suggestion Engine ---
            def suggest_routing(latest, caps, thres):
                suggestions = []
                # Calculate utilization %
                utilization = {z: latest[z] / caps[z] for z in caps}
                overloaded = [z for z in utilization if utilization[z] > thres]
                underloaded = [z for z in utilization if utilization[z] < 0.6]  # safe zones

                for zone in overloaded:
                    excess = int(latest[zone] - thres * caps[zone])
                    if not underloaded:
                        suggestions.append(f"⚠ {zone} overloaded, but no free gates. Increase capacity or slow inflow.")
                    else:
                        # Pick the freest gate
                        best = min(underloaded, key=lambda z: utilization[z])
                        suggestions.append(f"➡ Redirect ~{excess} people from {zone} → {best} (free space available).")

                return suggestions


            # --- Show Routing Suggestions ---
            st.subheader("🚦 AI Routing Suggestions")
            routing = suggest_routing(latest_counts(df), capacities, threshold)
            if routing:
                for r in routing:
                    st.info(r)
            else:
                st.success("✅ No rerouting needed. Flow is balanced.")

            # Plot with forecasts
            fig,ax = plt.subplots()
            for g in ["Gate A","Gate B","Gate C","Gate D"]:
                series = df[df["zone"]==g].set_index("timestamp")["count"]
                ax.plot(series.index, series.values, label=f"{g} actual")
                preds = ewma_forecast(series, ewma_alpha, forecast_horizon)
                future_idx = pd.date_range(series.index[-1], periods=forecast_horizon+1, freq="S")[1:]
                ax.plot(future_idx, preds, "--", label=f"{g} forecast")
            ax.legend()
            st.pyplot(fig)

        time.sleep(refresh_secs)
