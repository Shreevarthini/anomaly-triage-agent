import pandas as pd
import numpy as np

def detect_zscore_anomalies(df: pd.DataFrame, column: str = "order_count", z_thresh: float = 3.0) -> pd.DataFrame:
    mean = df[column].mean()
    std = df[column].std()
    df = df.copy()
    df["z_score"] = (df[column] - mean) / std
    df["is_anomaly_zscore"] = df["z_score"].abs() > z_thresh
    return df

def detect_volume_drop(df: pd.DataFrame, column: str = "order_count", drop_pct: float = 0.5, window: int = 5) -> pd.DataFrame:
    df = df.copy()
    rolling_median = df[column].rolling(window=window, min_periods=1).median().shift(1)
    df["rolling_median"] = rolling_median
    df["is_anomaly_drop"] = df[column] < (rolling_median * (1 - drop_pct))
    return df

def run_all_detectors(df: pd.DataFrame) -> pd.DataFrame:
    df = detect_zscore_anomalies(df)
    df = detect_volume_drop(df)
    df["is_anomaly"] = df["is_anomaly_zscore"] | df["is_anomaly_drop"]
    return df
    
def describe_anomaly(row: pd.Series) -> str:
    timestamp = row["timestamp"]
    count = row["order_count"]

    if row.get("is_anomaly_zscore"):
        return (
            f"At {timestamp}, order_count spiked to an unusual value of {count} "
            f"(z-score {row['z_score']:.2f}) for the checkout-service pipeline."
        )
    elif row.get("is_anomaly_drop"):
        return (
            f"At {timestamp}, order_count dropped sharply to {count} "
            f"(well below the recent rolling median of {row['rolling_median']:.1f}) "
            f"for the checkout-service pipeline."
        )
    else:
        return f"At {timestamp}, an anomaly was flagged with order_count={count}."
if __name__ == "__main__":
    df = pd.read_csv("orders_data.csv")
    result = run_all_detectors(df)

    flagged = result[result["is_anomaly"]]
    print("Flagged anomalies:")
    print(flagged[["timestamp", "order_count", "z_score", "is_anomaly_zscore", "is_anomaly_drop"]])
    injected = result[result["anomaly_injected"]]
    print("\nRows we deliberately injected as anomalies:")
    print(injected[["timestamp", "order_count", "is_anomaly"]])