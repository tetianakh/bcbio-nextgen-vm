#!/bin/bash
#SBATCH --cpus-per-task=1
#SBATCH --mem=2000
#SBATCH -p cloud
#SBATCH -t 0
#SBATCH --output=/home/ubuntu/testrun/slurm_%j.out
#SBATCH --error=/home/ubuntu/testrun/slurm_%j.err
#SBATCH --workdir=/mnt/S3/workdir
bcbio_vm.py  --datadir=/home/ubuntu/src/bcbio-nextgen/tests/data/test_fusion ipython --systemconfig=/home/ubuntu/system_config.yaml /home/ubuntu/run_info-fusion.yaml slurm cloud --numcores 8 -r timelimit=0 --timeout 15
