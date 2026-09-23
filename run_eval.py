import asyncio
from eval_cases import EVAL_CASES
from agent_mcp import investigate_anomaly


async def score_agent():
    results = []

    for case in EVAL_CASES:
        print(f"Running case: {case['id']}")
        diagnosis = await investigate_anomaly(case["anomaly"])
        diagnosis_lower = diagnosis.lower()

        matched = [kw for kw in case["expected_keywords"] if kw.lower() in diagnosis_lower]
        correct = len(matched) > 0

        results.append({
            "id": case["id"],
            "correct": correct,
            "matched_keywords": matched,
            "diagnosis": diagnosis,
        })

        status = "PASS" if correct else "FAIL"
        print(f"  [{status}] matched: {matched or 'none'}")
        await asyncio.sleep(20)  

    accuracy = sum(r["correct"] for r in results) / len(results)
    print(f"\nAccuracy: {accuracy:.0%} ({sum(r['correct'] for r in results)}/{len(results)})")

    return accuracy, results


if __name__ == "__main__":
    asyncio.run(score_agent())