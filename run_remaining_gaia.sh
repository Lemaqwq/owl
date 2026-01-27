#!/bin/bash
# Parallel GAIA Benchmark - Remaining Tasks
# Partition 4: 11 tasks remaining (indices 154-164)
# Split across 5 workers

set -e

echo "Starting 5 parallel GAIA evaluation sessions for remaining tasks..."

CONDA_INIT="source /Users/lihengchen/opt/anaconda3/etc/profile.d/conda.sh"
WORKDIR="/Users/lihengchen/Github/owl"
ENV="owl-gaia"

# Split indices 154-164 (11 tasks) across 5 workers
sleep 1 && tmux new-session -d -s gaia_r0 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce.py --start-idx 154 --end-idx 157 --partition 4_0'"
# sleep 1 && tmux new-session -d -s gaia_r1 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce.py --start-idx 157 --end-idx 159 --partition 4_1'"
# sleep 1 && tmux new-session -d -s gaia_r2 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce.py --start-idx 159 --end-idx 161 --partition 4_2'"
# sleep 1 && tmux new-session -d -s gaia_r3 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce.py --start-idx 161 --end-idx 163 --partition 4_3'"
# sleep 1 && tmux new-session -d -s gaia_r4 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce.py --start-idx 163 --end-idx 165 --partition 4_4'"

echo "Started 5 parallel GAIA evaluation sessions for remaining tasks"
echo ""
echo "Task distribution (indices 154-164):"
echo "  gaia_r0: partition 4_0, indices 154-156 (3 tasks)"
echo "  gaia_r1: partition 4_1, indices 157-158 (2 tasks)"
echo "  gaia_r2: partition 4_2, indices 159-160 (2 tasks)"
echo "  gaia_r3: partition 4_3, indices 161-162 (2 tasks)"
echo "  gaia_r4: partition 4_4, indices 163-164 (2 tasks)"
echo ""
echo "Use 'tmux attach -t gaia_r0' to view session 0, etc."
echo "Use 'tmux ls' to list all sessions"
echo "Use 'tmux kill-session -t gaia_r0' to kill a session"
