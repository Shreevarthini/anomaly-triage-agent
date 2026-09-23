def query_logs(service: str, time_window_minutes: int = 60) -> str:
    fake_logs = {
        "checkout-service": "12:44 ERROR PaymentGatewayTimeout: upstream payment provider not responding\n12:45 ERROR PaymentGatewayTimeout: retry failed",
        "order-service": "No errors in this window. Order processing nominal.",
    }
    return fake_logs.get(service, f"No logs found for service '{service}'.")

def query_recent_deploys(service: str) -> str:
    fake_deploys = {
        "checkout-service": "No recent deploys in the last 24 hours.",
        "order-service": "Deploy at 13:40: 'v2.3.1 - increased cache TTL for product listings'.",
    }
    return fake_deploys.get(service, f"No deploy history found for '{service}'.")