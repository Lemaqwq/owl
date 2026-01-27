#!/usr/bin/env python3
"""
GAIA Benchmark Watcher Script for Claude Models

Monitors tmux sessions and ensures 5 workers are always running for unfinished partitions.
"""

import json
import os
import subprocess
import time
from typing import Dict, List, Set

# Partition configuration (5 nodes, 33 tasks each)
PARTITIONS = {
    0: {"start": 0, "end": 33, "size": 33},
    1: {"start": 33, "end": 66, "size": 33},
    2: {"start": 66, "end": 99, "size": 33},
    3: {"start": 99, "end": 132, "size": 33},
    4: {"start": 132, "end": 165, "size": 33},
}

RESULT_DIR = "results/workforce"
RESULT_FILE_PATTERN = "workforce_all_pass1_claude_p{}.json"
MAX_WORKERS = 5
CHECK_INTERVAL = 60  # seconds
SESSION_PREFIX = "claude"
PYTHON_SCRIPT = "run_gaia_workforce_claude.py"
CONDA_ENV = "owl-gaia"
WORKDIR = "/Users/lihengchen/Github/owl"


def get_running_claude_sessions() -> Set[int]:
    """Get the set of currently running claude tmux session partition numbers."""
    running = set()
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.startswith(SESSION_PREFIX):
                    try:
                        partition = int(line.replace(SESSION_PREFIX, ""))
                        running.add(partition)
                    except ValueError:
                        pass
    except Exception as e:
        print(f"Error getting tmux sessions: {e}")
    return running


def is_partition_finished(partition: int) -> bool:
    """
    Check if a partition is finished.

    A partition is finished if:
    1. The result file exists
    2. The number of results equals the partition size
    3. No model_answer is null
    """
    result_file = os.path.join(RESULT_DIR, RESULT_FILE_PATTERN.format(partition))

    if not os.path.exists(result_file):
        print(f"  Partition {partition}: Result file not found")
        return False

    try:
        with open(result_file, "r") as f:
            results = json.load(f)

        if not isinstance(results, list):
            print(f"  Partition {partition}: Invalid result format (not a list)")
            return False

        expected_size = PARTITIONS[partition]["size"]
        actual_size = len(results)

        if actual_size < expected_size:
            print(f"  Partition {partition}: Incomplete ({actual_size}/{expected_size} tasks)")
            return False

        # Check for null model_answers
        null_answers = [r for r in results if r.get("model_answer") is None]
        if null_answers:
            print(f"  Partition {partition}: Has {len(null_answers)} null model_answers")
            return False

        print(f"  Partition {partition}: FINISHED ({actual_size} tasks completed)")
        return True

    except json.JSONDecodeError as e:
        print(f"  Partition {partition}: JSON decode error: {e}")
        return False
    except Exception as e:
        print(f"  Partition {partition}: Error reading result: {e}")
        return False


def start_partition(partition: int) -> bool:
    """Start a tmux session for the given partition."""
    config = PARTITIONS[partition]
    session_name = f"{SESSION_PREFIX}{partition}"
    cmd = f"cd {WORKDIR} && conda activate {CONDA_ENV} && python {PYTHON_SCRIPT} --start-idx {config['start']} --end-idx {config['end']} --partition {partition}"

    try:
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name, "bash", "-c", cmd],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"  Started session {session_name}: tasks {config['start']}-{config['end']}")
            return True
        else:
            print(f"  Failed to start session {session_name}: {result.stderr}")
            return False
    except Exception as e:
        print(f"  Error starting session {session_name}: {e}")
        return False


def get_unfinished_partitions() -> List[int]:
    """Get list of unfinished partitions."""
    unfinished = []
    for partition in PARTITIONS:
        if not is_partition_finished(partition):
            unfinished.append(partition)
    return unfinished


def main():
    print("=" * 60)
    print("GAIA Benchmark Watcher (Claude Models)")
    print(f"Max workers: {MAX_WORKERS}")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print(f"Result pattern: {RESULT_FILE_PATTERN}")
    print("=" * 60)

    while True:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking status...")

        # Get current state
        running_sessions = get_running_claude_sessions()
        print(f"Running sessions: {sorted(running_sessions) if running_sessions else 'None'}")

        # Check which partitions are finished
        print("Checking partition status:")
        unfinished_partitions = get_unfinished_partitions()

        if not unfinished_partitions:
            print("\nAll partitions are finished!")
            break

        print(f"\nUnfinished partitions: {unfinished_partitions}")

        # Determine which unfinished partitions are not running
        not_running = [p for p in unfinished_partitions if p not in running_sessions]
        print(f"Unfinished and not running: {not_running}")

        # Calculate how many workers we need to start
        current_workers = len(running_sessions)
        workers_to_start = min(MAX_WORKERS - current_workers, len(not_running))

        print(f"Current workers: {current_workers}, Need to start: {workers_to_start}")

        # Start new workers
        if workers_to_start > 0:
            for i in range(workers_to_start):
                partition = not_running[i]
                print(f"Starting partition {partition}...")
                start_partition(partition)
                time.sleep(2)  # Small delay between starts

        # Wait before next check
        print(f"\nWaiting {CHECK_INTERVAL} seconds before next check...")
        time.sleep(CHECK_INTERVAL)

    print("\nWatcher completed. All partitions finished.")


if __name__ == "__main__":
    main()
