#!/bin/bash
# Parallel GAIA Benchmark Evaluation with Claude Models
# Partitions for 165 tasks across 5 workers:
# 0-33, 33-66, 66-99, 99-132, 132-165

set -e

echo "Starting 5 parallel GAIA evaluation sessions with Claude models..."

CONDA_INIT="source /Users/lihengchen/opt/anaconda3/etc/profile.d/conda.sh"
WORKDIR="/Users/lihengchen/Github/owl"
ENV="owl-gaia"

tmux new-session -d -s claude0 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce_claude.py --start-idx 0 --end-idx 33 --partition 0'"
# sleep 1 && tmux new-session -d -s claude1 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce_claude.py --start-idx 33 --end-idx 66 --partition 1'"
# sleep 1 && tmux new-session -d -s claude2 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce_claude.py --start-idx 66 --end-idx 99 --partition 2'"
# sleep 1 && tmux new-session -d -s claude3 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce_claude.py --start-idx 99 --end-idx 132 --partition 3'"
# sleep 1 && tmux new-session -d -s claude4 "bash -c '$CONDA_INIT && conda activate $ENV && cd $WORKDIR && python run_gaia_workforce_claude.py --start-idx 132 --end-idx 165 --partition 4'"

echo "Started 5 parallel GAIA evaluation sessions with Claude models"
echo ""
echo "Task distribution:"
echo "  claude0: tasks 0-32   (33 tasks)"
echo "  claude1: tasks 33-65  (33 tasks)"
echo "  claude2: tasks 66-98  (33 tasks)"
echo "  claude3: tasks 99-131 (33 tasks)"
echo "  claude4: tasks 132-165 (33 tasks)"
echo ""
echo "Use 'tmux attach -t claude0' to view session 0, etc."
echo "Use 'tmux ls' to list all sessions"
echo "Use 'tmux kill-session -t claude0' to kill a session"
