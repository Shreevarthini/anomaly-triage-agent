import pandas as pd
import numpy as np

def detect_zscore_anomalies(df: pd.DataFrame, column: str = "order_count", z_thresh: float = 3.5) -> pd.DataFrame:
    mean = df[column].mean()
    std = df[column].std()
    df = df.copy()
    df["z_score"] = (df[column] - mean) / std
    df["is_anomaly_zscore"] = df["z_score"].abs() > z_thresh
    return df

def detect_volume_drop(df: pd.DataFrame, column: str = "order_count", z_thresh: float = 3.5) -> pd.DataFrame:
    df = df.copy()
    df["hour_of_day"] = pd.to_datetime(df["timestamp"]).dt.hour
    grouped = df.groupby("hour_of_day")[column]

    hourly_median = grouped.transform("median")
    mad = grouped.transform(lambda x: (x - x.median()).abs().median())
    mad_safe = mad.replace(0, 1)  

    modified_z = 0.6745 * (df[column] - hourly_median) / mad_safe

    df["hourly_median"] = hourly_median
    df["modified_z_drop"] = modified_z
    df["is_anomaly_drop"] = modified_z < -z_thresh
    return df

def run_all_detectors(df: pd.DataFrame) -> pd.DataFrame:
    df = detect_zscore_anomalies(df)
    df = detect_volume_drop(df)
    df["is_anomaly_zero"] = (df["order_count"] == 0) & (df["hourly_median"] > 5)
    df["is_anomaly"] = df["is_anomaly_zscore"] | df["is_anomaly_drop"] | df["is_anomaly_zero"]
    return df
    
def describe_anomaly(row: pd.Series) -> str:
    timestamp = row["timestamp"]
    count = row["order_count"]

    if row.get("is_anomaly_zero"):
        return (
            f"At {timestamp}, order_count dropped to exactly 0 for the checkout-service "
            f"pipeline — during an hour that is normally active (typical median of "
            f"{row['hourly_median']:.0f} orders). This is a complete stop in order processing."
        )
    elif row.get("is_anomaly_zscore"):
        return (
            f"At {timestamp}, order_count spiked to an unusual value of {count} "
            f"(z-score {row['z_score']:.2f}) for the checkout-service pipeline."
        )
    elif row.get("is_anomaly_drop"):
        return (
            f"At {timestamp}, order_count dropped sharply to {count} "
            f"(well below the typical value of {row['hourly_median']:.1f} for this hour of day) "
            f"for the checkout-service pipeline."
        )
    else:
        return f"At {timestamp}, an anomaly was flagged with order_count={count} for the checkout-service pipeline."
if __name__ == "__main__":
    df = pd.read_csv("data/orders_data.csv")
    result = run_all_detectors(df)

    flagged = result[result["is_anomaly"]]
    print("Flagged anomalies:")
    print(flagged[["timestamp", "order_count", "z_score", "is_anomaly_zscore", "is_anomaly_drop"]])
    injected = result[result["anomaly_injected"]]
    print("\nRows we deliberately injected as anomalies:")
    print(injected[["timestamp", "order_count", "is_anomaly"]])
    # print("\nDebug: modified z-score details for the injected drop row")
    # print(result.loc[[112], ["timestamp", "order_count", "hourly_median", "modified_z_drop"]])