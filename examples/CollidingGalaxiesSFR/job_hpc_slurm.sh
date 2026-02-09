#!/bin/bash
#SBATCH --job-name=galaxy_collision
#SBATCH --nodes=1
#SBATCH --ntasks=64
#SBATCH --time=72:00:00
#SBATCH --partition=defq
#SBATCH --output=run_%j.log

# Add GSL to library path (if installed in home directory)
export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH

# Load required modules (adjust for your HPC system)
module purge
module load openmpi/gcc/64/1.10.7
module load hdf5/1.10.1
module load fftw3/openmpi/gcc/64/3.3.8
module load hwloc/1.11.11

# Show loaded modules
module list

# Set working directory
cd $SLURM_SUBMIT_DIR

# Auto-detect restart
if [ -f "output/restartfiles/restart.0" ]; then
    echo "=== Restarting from checkpoint at $(date) ==="
    RESTART_FLAG=1
else
    echo "=== Starting new simulation at $(date) ==="
    RESTART_FLAG=0
fi

# Run simulation
mpirun -np $SLURM_NTASKS ./Gadget4 param.txt $RESTART_FLAG
