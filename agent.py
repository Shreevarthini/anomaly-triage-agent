import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tools import query_logs, query_recent_deploys

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

AVAILABLE_TOOLS = {
    "query_logs": query_logs,
    "query_recent_deploys": query_recent_deploys,
}

def investigate_anomaly(anomaly_description: str) -> str:
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            tools=[query_logs, query_recent_deploys],
            system_instruction=(
                "You are a site-reliability agent investigating a data pipeline anomaly. "
                "Use the available tools to gather evidence, then give a short diagnosis: "
                "likely root cause, and a severity of LOW, MEDIUM, or HIGH."
            ),
        ),
    )
    response = chat.send_message(anomaly_description)
    return response.text

if __name__ == "__main__":
    result = investigate_anomaly(
        "Order volume dropped to near-zero around 12:46 for the checkout-service pipeline."
    )
    print(result)