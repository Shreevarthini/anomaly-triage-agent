import asyncio
import pandas as pd
from anomaly_detector import run_all_detectors, describe_anomaly
from agent_mcp import investigate_anomaly


async def run_pipeline(csv_path: str = "data/orders_data.csv"):
    df = pd.read_csv(csv_path)
    result = run_all_detectors(df)
    flagged = result[result["is_anomaly"]]

    if flagged.empty:
        print("No anomalies detected. Pipeline healthy.")
        return

    print(f"Detected {len(flagged)} anomaly(ies). Investigating each...\n")

    for _, row in flagged.iterrows():
        description = describe_anomaly(row)
        print(f"ANOMALY: {description}")
        diagnosis = await investigate_anomaly(description)
        print(f"DIAGNOSIS:\n{diagnosis}\n")
        print("-" * 60)
        await asyncio.sleep(20)


if __name__ == "__main__":
    asyncio.run(run_pipeline())