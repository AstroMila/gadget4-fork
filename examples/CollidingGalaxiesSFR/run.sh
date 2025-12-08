#!/bin/bash
# Script to run the CollidingGalaxiesSFR simulation
# Usage: ./run.sh [restart_flag]
#   restart_flag: optional, use "1" to restart from checkpoint

cd "$(dirname "$0")"  # Change to script directory

if [ "$1" == "1" ]; then
    echo "=== Restarting from checkpoint at $(date) ===" | tee -a run.log
    time mpirun -np 4 ./Gadget4 param.txt 1 2>&1 | tee -a run.log
else
    echo "=== Starting new simulation at $(date) ===" | tee run.log
    time mpirun -np 4 ./Gadget4 param.txt 2>&1 | tee run.log
fi
