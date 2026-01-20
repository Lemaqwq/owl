#!/bin/bash
# Parallel GAIA Benchmark Evaluation
# Partitions for 165 tasks across 5 workers:
# 0-33, 33-66, 66-99, 99-132, 132-165

set -e

echo "Starting 5 parallel GAIA evaluation sessions..."

CONDA_INIT="source /Users/lihengchen/opt/anaconda3/etc/profile.d/conda.sh"
WORKDIR="/Users/lihengchen/Github/owl"
ENV="owl-gaia"

# tmux new-session -d -s gaia0 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce.py --start-idx 0 --end-idx 33 --partition 0'"
tmux new-session -d -s gaia1 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce.py --start-idx 33 --end-idx 66 --partition 1'"
# tmux new-session -d -s gaia2 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce.py --start-idx 66 --end-idx 99 --partition 2'"
# tmux new-session -d -s gaia3 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce.py --start-idx 99 --end-idx 132 --partition 3'"
tmux new-session -d -s gaia4 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce.py --start-idx 132 --end-idx 165 --partition 4'"

echo "Started 5 parallel GAIA evaluation sessions"
echo ""
echo "Task distribution:"
echo "  gaia0: tasks 0-32   (33 tasks)"
echo "  gaia1: tasks 33-65  (33 tasks)"
echo "  gaia2: tasks 66-98  (33 tasks)"
echo "  gaia3: tasks 99-131 (33 tasks)"
echo "  gaia4: tasks 132-165 (33 tasks)"
echo ""
echo "Use 'tmux attach -t gaia0' to view session 0, etc."
echo "Use 'tmux ls' to list all sessions"
echo "Use 'tmux kill-session -t gaia0' to kill a session"
