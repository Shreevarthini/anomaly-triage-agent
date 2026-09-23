EVAL_CASES = [
    {
        "id": "payment-timeout-drop",
        "anomaly": "Order volume dropped sharply to near-zero for the checkout-service pipeline around 12:46.",
        "expected_keywords": ["payment", "timeout", "gateway"],
    },
    {
        "id": "traffic-spike-no-deploy",
        "anomaly": "Order count spiked to 8x the baseline for the checkout-service pipeline, with no recent deploys.",
        "expected_keywords": ["traffic", "spike", "bot"],
    },
    {
        "id": "clear-bad-deploy",
        "anomaly": "Error rate for order-service jumped immediately after a deploy 10 minutes ago.",
        "expected_keywords": ["deploy", "recent", "release"],
    },
    {
        "id": "no-errors-quiet-service",
        "anomaly": "order-service order_count dropped slightly overnight with no errors logged.",
        "expected_keywords": ["no errors", "nominal", "low"],
    },
]