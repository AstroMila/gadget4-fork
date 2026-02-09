# GADGET-4 on HPC ATOS - Complete Guide

This guide covers running the CollidingGalaxiesSFR example on HPC ATOS Kragujevac.

## System Specifications

- **Compute Nodes:** dgx01-04 (DGX systems)
- **Cores per node:** 256
- **Memory per node:** 1010 GB
- **Scheduler:** SLURM
- **Max job time:** 3 days (72 hours)

## Initial Setup (One-time)

### 1. Clone Repository
```bash
git clone https://github.com/AstroMila/gadget4-fork.git gadget4_mila
cd gadget4_mila
```

### 2. Install GSL Library (in home directory)
```bash
cd ~
wget https://ftp.gnu.org/gnu/gsl/gsl-2.7.tar.gz
tar xzf gsl-2.7.tar.gz
cd gsl-2.7
./configure --prefix=$HOME/local
make -j 32
make install
cd ..
rm -rf gsl-2.7 gsl-2.7.tar.gz

# Add to bashrc (permanent)
echo 'export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### 3. Setup Build System

**Create library paths file:**
```bash
cd ~/projects/Gadget4/mila/buildsystem
cat > Makefile.path.hpc-atos << 'EOF'
# Library paths for HPC ATOS Kragujevac

# GSL paths (installed in home directory)
GSL_INCL   = -I$(HOME)/local/include
GSL_LIBS   = -L$(HOME)/local/lib

# FFTW3 paths
FFTW_INCL  = -I/cm/shared/apps/fftw/openmpi/gcc/64/3.3.8/include
FFTW_LIBS  = -L/cm/shared/apps/fftw/openmpi/gcc/64/3.3.8/lib

# HDF5 paths
HDF5_INCL  = -I/cm/shared/apps/hdf5/1.10.1/include
HDF5_LIBS  = -L/cm/shared/apps/hdf5/1.10.1/lib

# HWLOC paths
HWLOC_INCL = -I/cm/shared/apps/hwloc/1.11.11/include
HWLOC_LIBS = -L/cm/shared/apps/hwloc/1.11.11/lib
EOF
```

**Create system type file:**
```bash
cd ~/projects/Gadget4/mila
echo 'SYSTYPE="HPC-ATOS"' > Makefile.systype
```

**Edit Makefile** (add after line 110):
```bash
nano Makefile
# Add these lines after the Generic-gcc block:
ifeq ($(SYSTYPE),"HPC-ATOS")
include buildsystem/Makefile.path.hpc-atos
include buildsystem/Makefile.comp.gcc
endif
```

### 4. Transfer Initial Conditions

From your local machine:
```bash
scp /path/to/ExampleICs/ics_collision_g4.dat username@hpc-atos:~/projects/Gadget4/mila/ExampleICs/
```

### 5. Build GADGET-4

```bash
cd ~/projects/Gadget4/mila

# Load required modules
module load openmpi/gcc/64/1.10.7
module load hdf5/1.10.1
module load fftw3/openmpi/gcc/64/3.3.8
module load hwloc/1.11.11

# Copy configuration for this example
cp examples/CollidingGalaxiesSFR/Config.sh .

# Clean and build
make clean
make -j 16

# Copy executable to example directory
cp Gadget4 examples/CollidingGalaxiesSFR/
```

## Interactive Test Run (Quick Test)

Use this to verify everything works before submitting long jobs.

### 1. Request Interactive Session
```bash
# Request 10 minutes on compute node with 16 cores
srun --nodes=1 --ntasks=16 --time=10:00 --pty bash
```

### 2. Load Modules and Run
```bash
# Load required modules
module load openmpi/gcc/64/1.10.7 hdf5/1.10.1 fftw3/openmpi/gcc/64/3.3.8 hwloc/1.11.11

# Navigate to example
cd ~/projects/Gadget4/mila/examples/CollidingGalaxiesSFR

# Run 1-minute test (make sure param.txt has TimeLimitCPU=60)
mpirun -np 16 ./Gadget4 param_shortTest.txt
```

### 3. Exit Interactive Session
```bash
exit
```

## Production SLURM Jobs

### Configuration Files

**param.txt** (production settings):
```
TimeLimitCPU              259200  # 3 days in seconds
MaxMemSize                15000   # MB per process (for 64 processes)
```

**job_hpc_slurm.sh** (SLURM job script):
```bash
#!/bin/bash
#SBATCH --job-name=galaxy_collision
#SBATCH --nodes=1
#SBATCH --ntasks=64              # 64 MPI processes
#SBATCH --time=72:00:00          # 3 days
#SBATCH --partition=defq
#SBATCH --output=run_%j.log

# Add GSL to library path
export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH

# Load required modules
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
```

### Submitting Jobs

```bash
cd ~/projects/Gadget4/mila/examples/CollidingGalaxiesSFR

# Submit job
sbatch job_hpc_slurm.sh

# Check job status
squeue -u $USER

# Watch log file
tail -f run_*.log
# (Press Ctrl+C to exit tail without stopping simulation)
```

### Restarting Jobs

The job script auto-detects restarts. If the simulation hits the time limit:

```bash
# Just resubmit - it will automatically continue from checkpoint
sbatch job_hpc_slurm.sh
```

**Important:** Always use the **same number of processes** for restarts as the original run.

## Monitoring Progress

### Check Job Status
```bash
# View your jobs
squeue -u $USER

# View all jobs
squeue

# Check which nodes are idle
sinfo
```

### Check Simulation Progress
```bash
cd ~/projects/Gadget4/mila/examples/CollidingGalaxiesSFR

# View recent progress (time stamps)
grep "Sync-Point.*Time:" run_*.log | tail -10

# Count snapshots created
ls output/snapshot_*.hdf5 | wc -l

# List latest snapshots
ls -lht output/snapshot_*.hdf5 | head -5

# Check star formation rate
tail sfrrate.txt
```

### Understanding Time
- **Time:** Simulation time in Gyr (0 to 4.0 Gyr target)
- **TimeBetSnapshot:** 0.05 Gyr (snapshot every 50 million years)
- **Total snapshots expected:** 81 (0 to 80)

## Memory and Performance Tuning

### Recommended Configurations

**For 1.6M particles (CollidingGalaxiesSFR):**

| Processes | MaxMemSize | Total Memory | Speed  | Use Case |
|-----------|------------|--------------|--------|----------|
| 16        | 40000 MB   | ~640 GB      | Slower | Testing  |
| 32        | 20000 MB   | ~640 GB      | Fast   | Balanced |
| 64        | 15000 MB   | ~960 GB      | Faster | Recommended |
| 128       | 7000 MB    | ~896 GB      | Fastest| MPI overhead |

**To change configuration:**
1. Edit `param.txt`: adjust `MaxMemSize`
2. Edit `job_hpc_slurm.sh`: adjust `--ntasks`
3. **Important:** Delete `output/*` if changing process count mid-simulation

## File Structure

```
examples/CollidingGalaxiesSFR/
├── Config.sh                  # Physics modules configuration
├── param.txt                  # Production parameters (3 days)
├── param_shortTest.txt        # Test parameters (1 minute)
├── job_hpc_slurm.sh          # SLURM job script
├── Gadget4                    # Compiled executable
├── TREECOOL                   # Cooling table
├── output/                    # Simulation output
│   ├── snapshot_*.hdf5       # Particle snapshots
│   └── restartfiles/         # Checkpoint files
├── eos.txt                    # Equation of state log
├── sfrrate.txt               # Star formation rate log
└── run_*.log                 # SLURM job logs
```

## Troubleshooting

### GSL Library Not Found
```bash
# Error: libgsl.so.25: cannot open shared object file
# Fix: Add to library path
export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH
# Make permanent by adding to ~/.bashrc
```

### MPI_ABORT Error on Restart
**Cause:** Process count mismatch (e.g., test with 16, restart with 64)

**Fix:** Clean output and start fresh:
```bash
rm -rf output/*
sbatch job_hpc_slurm.sh
```

### Job Pending (Won't Start)
```bash
# Check why job is waiting
squeue -u $USER

# Common reasons:
# - (Priority): Other jobs ahead in queue
# - (Resources): All nodes busy
# - (MaxCpuPerAccount): You hit your CPU limit
```

### OpenIB Warnings
Messages like "WARNING: No preset parameters were found for device mlx5_0" are **harmless** - these are InfiniBand network warnings that don't affect the simulation.

## Typical Workflow

1. **First run:**
   ```bash
   sbatch job_hpc_slurm.sh
   ```

2. **Monitor progress:**
   ```bash
   grep "Sync-Point.*Time:" run_*.log | tail -5
   ls output/snapshot_*.hdf5 | wc -l
   ```

3. **If job hits time limit (3 days):**
   ```bash
   # Check last time reached
   grep "reaching time-limit" run_*.log
   
   # Resubmit (auto-continues from checkpoint)
   sbatch job_hpc_slurm.sh
   ```

4. **When simulation completes:**
   ```bash
   # Look for this message in log:
   grep "Final time.*reached. Simulation ends" run_*.log
   
   # Verify all snapshots created
   ls output/snapshot_*.hdf5 | wc -l  # Should be 81
   ```

5. **Transfer results back:**
   ```bash
   # From local machine:
   rsync -avP username@hpc-atos:~/projects/Gadget4/mila/examples/CollidingGalaxiesSFR/output/ ./output/
   ```

## Performance Expectations

On DGX nodes with 64 processes:
- **Simulation speed:** ~0.5-0.7 Gyr per 3-day run
- **Total runs needed:** 6-8 restarts to reach 4.0 Gyr
- **Total wall time:** ~18-24 days
- **Disk space:** ~5 GB (81 snapshots @ ~60 MB each)

## Quick Reference Commands

```bash
# Submit job
sbatch job_hpc_slurm.sh

# Check status
squeue -u $USER

# Cancel job
scancel <JOBID>

# Watch progress
tail -f run_*.log

# Check simulation time
grep "Sync-Point.*Time:" run_*.log | tail -3

# Count snapshots
ls output/snapshot_*.hdf5 | wc -l

# Restart after time limit
sbatch job_hpc_slurm.sh
```

## Support

- **HPC Documentation:** Contact your HPC administrator
- **GADGET-4 Manual:** See `documentation/` directory
- **GitHub Issues:** https://github.com/AstroMila/gadget4-fork/issues
