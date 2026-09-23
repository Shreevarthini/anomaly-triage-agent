import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

def generate_normal_orders(hours=72, base_orders_per_hour=50):
    timestamps = [datetime.now() - timedelta(hours=hours - i) for i in range(hours)]
    order_counts = np.random.normal(loc=base_orders_per_hour, scale=5, size=hours).astype(int)
    order_counts = np.clip(order_counts, 0, None) 
    return pd.DataFrame({"timestamp": timestamps, "order_count": order_counts})

def inject_anomalies(df):
    df = df.copy()
    df["anomaly_injected"] = False
    df.loc[20, "order_count"] = 3
    df.loc[20, "anomaly_injected"] = True
    df.loc[45, "order_count"] = 400
    df.loc[45, "anomaly_injected"] = True

    return df

if __name__ == "__main__":
    df = generate_normal_orders()
    df = inject_anomalies(df)
    df.to_csv("orders_data.csv", index=False)
    print(df)
    print(f"\nSaved {len(df)} rows to orders_data.csv")