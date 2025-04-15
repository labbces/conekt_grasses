#!/bin/bash

#$ -q all.q
#$ -cwd
#$ -t 1
#$ -pe smp 1

module load miniconda3
conda activate conekt-grasses-snakemake-pipeline

# run complete YAATAP
snakemake -p -k --resources load=10 -s Snakefile --cluster "qsub -q all.q -V -l h={params.server} -cwd -pe smp {threads}" --jobs 10 --jobname "{rulename}.{jobid}" --use-conda --latency-wait 60

# generate DAG
#snakemake --dag | dot -Tsvg > dag.svg