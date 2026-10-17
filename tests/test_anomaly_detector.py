
import numpy as np
import pandas as pd
import pytest
 
from anomaly_detector import (
    add_hourly_modified_z,
    run_all_detectors,
)
 
 
def make_hour_group(hour: int, values: list[float], start: str = "2026-01-01") -> pd.DataFrame:
    """One row per day, all at the same hour of day."""
    base = pd.Timestamp(start)
    timestamps = [base + pd.Timedelta(days=i, hours=hour) for i in range(len(values))]
    return pd.DataFrame({"timestamp": timestamps, "order_count": values})
 
 
def combine(*groups: pd.DataFrame) -> pd.DataFrame:
    return pd.concat(groups, ignore_index=True)
 
 
def test_modified_z_matches_hand_calculation():
    # Hour 9 values: median = 11; absolute deviations = [1,1,0,1,1,0,19]
    # -> MAD = 1; so z for 30 = 0.6745 * (30 - 11) / 1 = 12.8155
    df = make_hour_group(9, [10, 12, 11, 10, 12, 11, 30])
    out = add_hourly_modified_z(df)
    assert out["hourly_median"].iloc[0] == 11
    assert out["modified_z"].iloc[-1] == pytest.approx(0.6745 * 19, rel=1e-6)
 
 
def test_spike_is_flagged():
    df = make_hour_group(9, [10, 12, 11, 10, 12, 11, 30])
    out = run_all_detectors(df)
    assert out["is_anomaly_spike"].iloc[-1]
    assert out["is_anomaly_spike"].sum() == 1
 
 
def test_drop_is_flagged():
    # median 51, MAD 1, z for 10 = 0.6745 * (10 - 51) = -27.7
    df = make_hour_group(14, [50, 52, 51, 50, 52, 51, 10])
    out = run_all_detectors(df)
    assert out["is_anomaly_drop"].iloc[-1]
    assert out["modified_z"].iloc[-1] < -3.5
 
 
def test_normal_daily_pattern_is_not_flagged():
    # A quiet 4am and a busy 3pm are both normal *for their hour*.
    # A single global z-score would be misled by this daily cycle.
    quiet = make_hour_group(4, [2, 3, 2, 3, 2, 3, 2])
    busy = make_hour_group(15, [100, 105, 98, 102, 99, 101, 103])
    out = run_all_detectors(combine(quiet, busy))
    assert not out["is_anomaly"].any()
 
 
def test_zero_rule_fires_in_active_hour():
    values = [100, 105, 98, 102, 99, 101, 0]
    out = run_all_detectors(make_hour_group(15, values))
    assert out["is_anomaly_zero"].iloc[-1]
    assert out["is_anomaly"].iloc[-1]
 
 
def test_zero_rule_ignores_normally_quiet_hour():
    # Median of ~2 orders: a zero here is ordinary, not an outage.
    out = run_all_detectors(make_hour_group(4, [2, 3, 2, 3, 2, 3, 0]))
    assert not out["is_anomaly_zero"].any()
 
 
def test_mad_zero_with_outlier_is_finite_and_flagged():
    # More than half the values are identical -> MAD == 0.
    # The MeanAD fallback must still produce a finite score and catch the outlier.
    df = make_hour_group(10, [10, 10, 10, 10, 10, 10, 25])
    out = add_hourly_modified_z(df)
    assert np.isfinite(out["modified_z"]).all()
    assert out["modified_z"].iloc[-1] > 3.5
    # ...and the identical values score exactly zero
    assert (out["modified_z"].iloc[:-1] == 0).all()
 
 
def test_constant_group_scores_zero_not_nan():
    out = add_hourly_modified_z(make_hour_group(11, [7, 7, 7, 7, 7, 7, 7]))
    assert (out["modified_z"] == 0).all()
    assert not out["modified_z"].isna().any()
 
 
def test_backward_compatible_columns_exist():
    out = run_all_detectors(make_hour_group(9, [10, 12, 11, 10, 12, 11, 30]))
    for col in ("z_score", "is_anomaly_zscore", "modified_z_drop", "is_anomaly_drop", "hourly_median"):
        assert col in out.columns