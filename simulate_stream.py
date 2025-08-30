import os
import time
import csv
import random
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
CSV_PATH = os.path.join(DATA_DIR, "crowd_stream.csv")

ZONES = ["Gate A", "Gate B", "Gate C", "Gate D"]

# Base capacities just for simulation realism (dashboard lets you change them for alerts)
CAPACITY = {
    "Gate A": 300,
    "Gate B": 280,
    "Gate C": 260,
    "Gate D": 240,
}

# Initialize counts randomly
state = {z: random.randint(int(0.2*CAPACITY[z]), int(0.5*CAPACITY[z])) for z in ZONES}

def write_header_if_needed(path):
    exists = os.path.exists(path)
    if not exists or os.path.getsize(path) == 0:
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp","zone","count"])

def simulate_step():
    global state
    # Occasionally inject a spike in a random gate to simulate congestion
    spike_gate = random.choice(ZONES) if random.random() < 0.05 else None
    rows = []
    now = datetime.utcnow().isoformat()

    for z in ZONES:
        drift = random.randint(-10, 12)  # small random walk
        if spike_gate == z:
            drift += random.randint(30, 60)  # spike
        new_val = max(0, min(CAPACITY[z], state[z] + drift))
        state[z] = new_val
        rows.append([now, z, new_val])
    return rows

def append_rows(path, rows):
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)

def main():
    print("Crowd simulator started. Writing to", CSV_PATH)
    print("Press Ctrl+C to stop.")
    write_header_if_needed(CSV_PATH)

    # Keep file from growing forever in long runs: truncate hourly
    last_hour = datetime.utcnow().hour

    try:
        while True:
            if datetime.utcnow().hour != last_hour:
                # rotate by truncating to header
                with open(CSV_PATH, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["timestamp","zone","count"])
                last_hour = datetime.utcnow().hour

            rows = simulate_step()
            append_rows(CSV_PATH, rows)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")

if __name__ == "__main__":
    main()
