import pandas as pd
import numpy as np
from load_real_data import load_and_aggregate

np.random.seed(42)

def generate_normal_orders(hours=336, base_orders_per_hour=None):
    df = pd.read_csv("data/real_orders_baseline.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.tail(hours).reset_index(drop=True)

def inject_anomalies(df):
    df = df.copy()
    df["anomaly_injected"] = False
    drop_idx = len(df) // 3
    spike_idx = (len(df) // 3) * 2

    normal_value = df.loc[drop_idx, "order_count"]
    df.loc[drop_idx, "order_count"] = 0
    df.loc[drop_idx, "anomaly_injected"] = True

    normal_value = df.loc[spike_idx, "order_count"]
    df.loc[spike_idx, "order_count"] = int(normal_value * 8)
    df.loc[spike_idx, "anomaly_injected"] = True

    return df

if __name__ == "__main__":
    df = generate_normal_orders()
    df = inject_anomalies(df)
    df.to_csv("data/orders_data.csv", index=False)
    print(df)
    print(f"\nSaved {len(df)} rows to orders_data.csv")