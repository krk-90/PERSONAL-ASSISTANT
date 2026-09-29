"""Simple authenticated API latency benchmark for the Personal Assistant.

Usage:
  EVAL_API_URL=http://127.0.0.1:8000/chat EVAL_BEARER_TOKEN=... \
  python evaluation/api_benchmark.py
"""
from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path

import requests

CASES = [
    "List my tasks.",
    "Create a test task named evaluation-check.",
    "What tasks are currently available?",
    "Explain how the assistant uses MCP tools.",
    "Summarize the assistant architecture.",
]
OUT = Path(__file__).resolve().parent / "api_benchmark_results.json"


def percentile(values: list[float], p: float) -> float:
    if len(values) == 1:
        return values[0]
    values = sorted(values)
    index = (len(values) - 1) * p / 100
    low, high = int(index), min(int(index) + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def main() -> None:
    url = os.environ["EVAL_API_URL"]
    token = os.environ.get("EVAL_BEARER_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    rows, latencies = [], []

    for query in CASES:
        started = time.perf_counter()
        try:
            response = requests.post(url, json={"query": query}, headers=headers, timeout=90)
            latency = (time.perf_counter() - started) * 1000
            latencies.append(latency)
            rows.append({"query": query, "status": response.status_code, "latency_ms": round(latency, 2), "ok": response.ok})
        except requests.RequestException as exc:
            rows.append({"query": query, "ok": False, "error": str(exc)})

    successful = sum(row["ok"] for row in rows)
    summary = {
        "requests": len(rows),
        "success_rate": successful / len(rows) if rows else 0.0,
        "latency_p50_ms": round(statistics.median(latencies), 2) if latencies else 0.0,
        "latency_p95_ms": round(percentile(latencies, 95), 2) if latencies else 0.0,
    }
    OUT.write_text(json.dumps({"summary": summary, "cases": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Results: {OUT}")


if __name__ == "__main__":
    main()
