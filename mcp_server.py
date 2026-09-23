import os
import requests
from dotenv import load_dotenv
load_dotenv()
from mcp.server.mcpserver import MCPServer


mcp = MCPServer("pipeline-tools")
@mcp.tool()
def post_slack_alert(summary: str, severity: str) -> str:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return "Slack webhook not configured — skipping post."

    payload = {"text": f"*[{severity}]* {summary}"}
    response = requests.post(webhook_url, json=payload)

    if response.status_code == 200:
        return "Diagnosis posted to Slack successfully."
    else:
        return f"Failed to post to Slack: {response.status_code} {response.text}"

@mcp.tool()
def query_logs(service: str, time_window_minutes: int = 60) -> str:
    if service == "checkout-service":
        return (
            "12:44 ERROR PaymentGatewayTimeout: upstream payment provider not responding\n"
            "12:45 ERROR PaymentGatewayTimeout: retry failed\n"
            "13:46 WARN TrafficSpike: order_count 8x above baseline, no errors logged\n"
            "13:46 INFO Possible causes: marketing campaign, bot traffic, or retry storm"
        )
    elif service == "order-service":
        return "No errors in this window. Order processing nominal."
    return f"No logs found for service '{service}'."
@mcp.tool()
def query_recent_deploys(service: str) -> str:
    fake_deploys = {
        "checkout-service": "No recent deploys in the last 24 hours.",
        "order-service": "Deploy at 13:40: 'v2.3.1 - increased cache TTL for product listings'.",
    }
    return fake_deploys.get(service, f"No deploy history found for '{service}'.")

if __name__ == "__main__":
    mcp.run()