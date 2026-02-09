#!/bin/bash
#SBATCH --job-name=galaxy_auto
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --time=48:00:00
#SBATCH --mem=64G
#SBATCH --partition=compute
#SBATCH --output=run_%j.log

# Load modules
module purge
module load openmpi hdf5 gsl fftw3 hwloc
module list

cd $SLURM_SUBMIT_DIR

# Check if restart files exist
if [ -f "output/restartfiles/restart.0" ]; then
    echo "=== Restarting from checkpoint at $(date) ==="
    RESTART_FLAG=1
else
    echo "=== Starting new simulation at $(date) ==="
    RESTART_FLAG=0
fi

# Run simulation
mpirun -np $SLURM_NTASKS ./Gadget4 param.txt $RESTART_FLAG

# Check if simulation finished or hit time limit
if grep -q "Final time.*reached. Simulation ends." run_${SLURM_JOB_ID}.log; then
    echo "Simulation completed successfully!"
else
    echo "Hit time limit, resubmitting job..."
    # Resubmit this script
    sbatch $0
fi
