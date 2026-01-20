#!/usr/bin/env python3
"""
Calculate GAIA Benchmark Success Rate

Summarizes results from all 6 partitions and calculates overall accuracy.
"""

import json
import os
from typing import Dict, List, Any

RESULT_DIR = "results/workforce"
RESULT_PATTERN = "workforce_all_pass1_gpt5_p{}.json"
NUM_PARTITIONS = 6


def load_partition_results(partition: int) -> List[Dict[str, Any]]:
    """Load results from a partition file."""
    file_path = os.path.join(RESULT_DIR, RESULT_PATTERN.format(partition))
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r") as f:
        return json.load(f)


def main():
    all_results = []
    partition_stats = []

    print("=" * 70)
    print("GAIA Benchmark Results Summary")
    print("=" * 70)
    print()

    # Load results from all partitions
    for p in range(NUM_PARTITIONS):
        results = load_partition_results(p)

        if not results:
            print(f"Partition {p}: No results found")
            partition_stats.append({
                "partition": p,
                "total": 0,
                "completed": 0,
                "correct": 0,
                "null_answers": 0,
            })
            continue

        total = len(results)
        null_answers = sum(1 for r in results if r.get("model_answer") is None)
        completed = total - null_answers
        correct = sum(1 for r in results if r.get("score") == True)

        partition_stats.append({
            "partition": p,
            "total": total,
            "completed": completed,
            "correct": correct,
            "null_answers": null_answers,
        })

        accuracy = (correct / completed * 100) if completed > 0 else 0
        print(f"Partition {p}: {correct}/{completed} correct ({accuracy:.2f}%), {null_answers} null answers, {total} total")

        all_results.extend(results)

    print()
    print("-" * 70)
    print("OVERALL SUMMARY")
    print("-" * 70)

    total_tasks = len(all_results)
    null_answers = sum(1 for r in all_results if r.get("model_answer") is None)
    completed_tasks = total_tasks - null_answers
    correct_tasks = sum(1 for r in all_results if r.get("score") == True)

    print(f"Total tasks:      {total_tasks}")
    print(f"Completed tasks:  {completed_tasks}")
    print(f"Null answers:     {null_answers}")
    print(f"Correct answers:  {correct_tasks}")
    print()

    if completed_tasks > 0:
        accuracy = correct_tasks / completed_tasks * 100
        print(f"Accuracy (completed): {correct_tasks}/{completed_tasks} = {accuracy:.2f}%")

    if total_tasks > 0:
        accuracy_total = correct_tasks / total_tasks * 100
        print(f"Accuracy (total):     {correct_tasks}/{total_tasks} = {accuracy_total:.2f}%")

    # Breakdown by level
    print()
    print("-" * 70)
    print("BREAKDOWN BY LEVEL")
    print("-" * 70)

    levels = {}
    for r in all_results:
        level = r.get("level", "unknown")
        if level not in levels:
            levels[level] = {"total": 0, "completed": 0, "correct": 0}
        levels[level]["total"] += 1
        if r.get("model_answer") is not None:
            levels[level]["completed"] += 1
        if r.get("score") == True:
            levels[level]["correct"] += 1

    for level in sorted(levels.keys()):
        stats = levels[level]
        acc = (stats["correct"] / stats["completed"] * 100) if stats["completed"] > 0 else 0
        print(f"Level {level}: {stats['correct']}/{stats['completed']} correct ({acc:.2f}%), {stats['total']} total")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
