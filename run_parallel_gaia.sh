#!/bin/bash
# Parallel GAIA Benchmark Evaluation
# Partitions for 165 tasks across 6 workers:
# 0-27, 28-55, 56-83, 84-111, 112-139, 140-165

set -e

echo "Starting 6 parallel GAIA evaluation sessions..."

tmux new-session -d -s gaia0 'python run_gaia_workforce.py --start-idx 0 --end-idx 28 --partition 0'
# tmux new-session -d -s gaia1 'python run_gaia_workforce.py --start-idx 28 --end-idx 56 --partition 1'
# tmux new-session -d -s gaia2 'python run_gaia_workforce.py --start-idx 56 --end-idx 84 --partition 2'
# tmux new-session -d -s gaia3 'python run_gaia_workforce.py --start-idx 84 --end-idx 112 --partition 3'
# tmux new-session -d -s gaia4 'python run_gaia_workforce.py --start-idx 112 --end-idx 140 --partition 4'
# tmux new-session -d -s gaia5 'python run_gaia_workforce.py --start-idx 140 --end-idx 165 --partition 5'

echo "Started 6 parallel GAIA evaluation sessions"
echo ""
echo "Task distribution:"
echo "  gaia0: tasks 0-27   (28 tasks)"
echo "  gaia1: tasks 28-55  (28 tasks)"
echo "  gaia2: tasks 56-83  (28 tasks)"
echo "  gaia3: tasks 84-111 (28 tasks)"
echo "  gaia4: tasks 112-139 (28 tasks)"
echo "  gaia5: tasks 140-165 (25 tasks)"
echo ""
echo "Use 'tmux attach -t gaia0' to view session 0, etc."
echo "Use 'tmux ls' to list all sessions"
echo "Use 'tmux kill-session -t gaia0' to kill a session"