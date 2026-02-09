#!/bin/bash
#SBATCH --job-name=galaxy_collision
#SBATCH --nodes=1
#SBATCH --ntasks=16              # Use 16 MPI processes (adjust based on HPC)
#SBATCH --time=48:00:00           # 48 hours (adjust to HPC limits)
#SBATCH --mem=64G                 # Total memory (adjust based on HPC)
#SBATCH --partition=compute       # Check HPC partition names
#SBATCH --output=run_%j.log       # %j = job ID

# Load required modules
module purge
module load openmpi/4.1.6         # Adjust versions
module load hdf5/1.10.10
module load gsl/2.7
module load fftw3/3.3.10
module load hwloc/2.9.0

# Show loaded modules for debugging
module list

# Set working directory
cd $SLURM_SUBMIT_DIR

# For initial run:
mpirun -np $SLURM_NTASKS ./Gadget4 param.txt

# For restart:
# mpirun -np $SLURM_NTASKS ./Gadget4 param.txt 1
