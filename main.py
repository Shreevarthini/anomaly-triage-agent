from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
from anomaly_detector import run_all_detectors, describe_anomaly
from agent_mcp import investigate_anomaly
from generate_data import generate_normal_orders, inject_anomalies

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_dashboard():
    """Serve the dashboard as the homepage."""
    return FileResponse("static/index.html")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "anomaly-triage-agent"}


@app.post("/run-pipeline")
async def run_pipeline_endpoint():
    df = generate_normal_orders()
    df = inject_anomalies(df)
    result = run_all_detectors(df)
    flagged = result[result["is_anomaly"]]

    if flagged.empty:
        return {"anomalies_found": 0, "results": []}

    results = []
    for _, row in flagged.iterrows():
        description = describe_anomaly(row)
        diagnosis = await investigate_anomaly(description)
        results.append({"anomaly": description, "diagnosis": diagnosis})

    return {"anomalies_found": len(flagged), "results": results}