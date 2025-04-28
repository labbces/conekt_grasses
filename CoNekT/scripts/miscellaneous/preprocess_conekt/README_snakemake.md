# Before you begin

Create a folder with the name of the project/species you are working on.

## 1. Clone this repository

Inside the folder you created, clone the repository below. 

'''bash
git clone https://github.com/labbces/conekt_grasses.git
'''

## 2. Install and set up the virtual environment

In the folder you created, install and configure the Conda virtual environment.

If you are using a cluster with the `module` software/tool management software, you will first have to load conda:

```bash
module load miniconda3
```

Be patient, as this installation may take a few minutes.

'''bash
cd CoNekT/scripts/miscellaneous/preprocess_conekt
conda env create -n conekt-grasses-snakemake-pipeline -f environment.yaml
'''

Once the installation is complete, activate the environment:

'''bash
conda activate conekt-grasses-snakemake-pipeline
'''

## 3. Configure software paths in config.yaml

Before running pipeline, review the `config.yaml` file. Some paths ind the configuration are user-specific, while others are cluster-specific. Therefore, whenever a new user intends to run the pipeline, the software paths must bve adjusted accordingly.

## 4. Adjust the Snakefile for proper inputs

In the file `Snakefile`, you will need to adjust the name of the CSV file with your samples (SRRs) and the reference transcriptome.

## 5. Run the pipeline

### 5.1 Run the pipeline only with the samples.csv

Start with a test run to ensure everything is set up correctly:

'''bash
snakemake -np
'''

This command will lst all planned steps, from downloading raw reads to generating quantification matrices and reports.

If everything looks correct, execute pipeline:

'''bash
qsub Snakefile.sh
'''

### 5.2 Run the pipeline if previously downloaded FASTQ files

