#!/usr/bin/env python3
"""Calculate total tokens from api_logs/stats directory."""

import json
from pathlib import Path
from collections import defaultdict


def calculate_tokens(stats_dir: str = "api_logs/stats") -> dict:
    """Calculate total tokens for each model and overall."""
    stats_path = Path(stats_dir)

    if not stats_path.exists():
        print(f"Error: {stats_dir} does not exist")
        return {}

    results = defaultdict(lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "total_calls": 0,
        "total_duration_ms": 0,
        "successful_calls": 0,
    })

    # Process each model directory
    for model_dir in stats_path.iterdir():
        if not model_dir.is_dir():
            continue

        model_name = model_dir.name

        # Process each JSONL file
        for jsonl_file in model_dir.glob("*.jsonl"):
            with open(jsonl_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        results[model_name]["prompt_tokens"] += data.get("prompt_tokens", 0)
                        results[model_name]["completion_tokens"] += data.get("completion_tokens", 0)
                        results[model_name]["total_tokens"] += data.get("total_tokens", 0)
                        results[model_name]["total_calls"] += 1
                        results[model_name]["total_duration_ms"] += data.get("duration_ms", 0)
                        if data.get("success", False):
                            results[model_name]["successful_calls"] += 1
                    except json.JSONDecodeError:
                        continue

    return dict(results)


def print_results(results: dict):
    """Print formatted results."""
    if not results:
        print("No data found.")
        return

    total_prompt = 0
    total_completion = 0
    total_tokens = 0
    total_calls = 0
    total_duration = 0

    print("=" * 80)
    print("TOKEN USAGE SUMMARY BY MODEL")
    print("=" * 80)

    for model, stats in sorted(results.items()):
        print(f"\n{model}")
        print("-" * 40)
        print(f"  Prompt tokens:     {stats['prompt_tokens']:>15,}")
        print(f"  Completion tokens: {stats['completion_tokens']:>15,}")
        print(f"  Total tokens:      {stats['total_tokens']:>15,}")
        print(f"  API calls:         {stats['total_calls']:>15,}")
        print(f"  Successful calls:  {stats['successful_calls']:>15,}")
        print(f"  Total duration:    {stats['total_duration_ms']/1000:>15,.2f}s")

        total_prompt += stats['prompt_tokens']
        total_completion += stats['completion_tokens']
        total_tokens += stats['total_tokens']
        total_calls += stats['total_calls']
        total_duration += stats['total_duration_ms']

    print("\n" + "=" * 80)
    print("GRAND TOTAL")
    print("=" * 80)
    print(f"  Prompt tokens:     {total_prompt:>15,}")
    print(f"  Completion tokens: {total_completion:>15,}")
    print(f"  Total tokens:      {total_tokens:>15,}")
    print(f"  Total API calls:   {total_calls:>15,}")
    print(f"  Total duration:    {total_duration/1000:>15,.2f}s")
    print("=" * 80)


if __name__ == "__main__":
    results = calculate_tokens()
    print_results(results)
