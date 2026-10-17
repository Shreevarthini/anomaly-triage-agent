"""Anomaly detection for hourly order-volume data.

Method
------
Order volume has a strong daily cycle, so every observation is compared with
other observations from the *same hour of day* (not with the whole series).
Within each hour-of-day group we compute the Modified Z-Score of Iglewicz &
Hoaglin (1993), which is built on the median and the Median Absolute
Deviation (MAD) instead of the mean and standard deviation, so the anomalies
we are looking for cannot inflate their own baseline:

    M_i = 0.6745 * (x_i - median) / MAD          flag if |M_i| > 3.5

Edge case: for count data MAD can be 0 (more than half the values in a group
are identical). Iglewicz & Hoaglin's recommended fallback is to use the mean
absolute deviation instead:

    M_i = (x_i - median) / (1.253314 * MeanAD)

A separate hard rule flags zero orders during normally-active hours, because a
total outage should never depend on a statistical threshold.

Known limitations (worth stating up front)
------------------------------------------
* Batch / in-sample: the baseline is computed over the whole history, so it
  includes the point being scored and uses "future" data. A production
  version would use a rolling window of recent weeks per hour-of-week.
* Hour-of-day only: weekday vs weekend seasonality is not modelled.
* Small groups: with few days of history per hour, median/MAD are noisy.
"""

import numpy as np
import pandas as pd

MAD_CONSISTENCY = 0.6745    # makes MAD comparable to a std-dev under normality
MEAN_AD_CONSISTENCY = 1.253314  # same idea, for the MeanAD fallback
DEFAULT_Z_THRESH = 3.5      # Iglewicz & Hoaglin's recommended cut-off
DEFAULT_MIN_ACTIVE_MEDIAN = 5   # hour counts as "normally active" above this


def add_hourly_modified_z(df: pd.DataFrame, column: str = "order_count") -> pd.DataFrame:
    """Add `hour_of_day`, `hourly_median` and `modified_z` (signed) columns."""
    df = df.copy()
    df["hour_of_day"] = pd.to_datetime(df["timestamp"]).dt.hour
    by_hour = df.groupby("hour_of_day")[column]

    median = by_hour.transform("median")
    abs_dev = (df[column] - median).abs()
    abs_dev_by_hour = abs_dev.groupby(df["hour_of_day"])
    mad = abs_dev_by_hour.transform("median")
    mean_ad = abs_dev_by_hour.transform("mean")

    # Equivalent to 0.6745 * dev / MAD, written as dev / scale so the MeanAD
    # fallback slots in cleanly when MAD == 0.
    scale = np.where(mad > 0, mad / MAD_CONSISTENCY, MEAN_AD_CONSISTENCY * mean_ad)
    deviation = (df[column] - median).to_numpy(dtype=float)
    # scale == 0 only happens when every value in the group equals the median,
    # i.e. deviation is 0 everywhere in that group -> score 0, not NaN/inf.
    z = np.divide(deviation, scale, out=np.zeros_like(deviation), where=scale > 0)

    df["hourly_median"] = median
    df["modified_z"] = z
    return df


def detect_modified_z_anomalies(
    df: pd.DataFrame, column: str = "order_count", z_thresh: float = DEFAULT_Z_THRESH
) -> pd.DataFrame:
    """Two-sided detection: spikes (z > t) and drops (z < -t)."""
    df = add_hourly_modified_z(df, column)
    df["is_anomaly_spike"] = df["modified_z"] > z_thresh
    df["is_anomaly_drop"] = df["modified_z"] < -z_thresh
    return df


def detect_zero_orders(
    df: pd.DataFrame,
    column: str = "order_count",
    min_active_median: float = DEFAULT_MIN_ACTIVE_MEDIAN,
) -> pd.DataFrame:
    """Hard rule: exactly zero orders in an hour that is normally active."""
    if "hourly_median" not in df.columns:
        df = add_hourly_modified_z(df, column)
    df = df.copy()
    df["is_anomaly_zero"] = (df[column] == 0) & (df["hourly_median"] > min_active_median)
    return df


def run_all_detectors(
    df: pd.DataFrame,
    column: str = "order_count",
    z_thresh: float = DEFAULT_Z_THRESH,
    min_active_median: float = DEFAULT_MIN_ACTIVE_MEDIAN,
) -> pd.DataFrame:
    df = detect_modified_z_anomalies(df, column, z_thresh)
    df = detect_zero_orders(df, column, min_active_median)
    df["is_anomaly"] = df["is_anomaly_spike"] | df["is_anomaly_drop"] | df["is_anomaly_zero"]

    # Backward-compatible aliases so main.py / agent code that still reads the
    # old column names keeps working. Remove once callers are updated.
    df["z_score"] = df["modified_z"]
    df["is_anomaly_zscore"] = df["is_anomaly_spike"]
    df["modified_z_drop"] = df["modified_z"]
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
    elif row.get("is_anomaly_spike"):
        return (
            f"At {timestamp}, order_count spiked to {count} "
            f"(modified z-score {row['modified_z']:.2f}; typical value for this hour is "
            f"{row['hourly_median']:.1f}) for the checkout-service pipeline."
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
    df = pd.read_csv("data/orders_data.csv")  # adjust the path to wherever your CSV lives
    result = run_all_detectors(df)

    flagged = result[result["is_anomaly"]]
    print("Flagged anomalies:")
    print(flagged[["timestamp", "order_count", "hourly_median", "modified_z",
                   "is_anomaly_spike", "is_anomaly_drop", "is_anomaly_zero"]])

    if "anomaly_injected" in result.columns:
        injected = result[result["anomaly_injected"]]
        print("\nRows we deliberately injected as anomalies:")
        print(injected[["timestamp", "order_count", "is_anomaly"]])