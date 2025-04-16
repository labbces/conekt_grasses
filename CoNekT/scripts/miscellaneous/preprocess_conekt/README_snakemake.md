# Before you begin

Create a folder with the name of the project/species you are working on.

## 1.Clone this repository

Inside the folder you created, clone the repository below. 

'''bash

git clone https://github.com/labbces/conekt_grasses/tree/conekt_documentacao/CoNekT/scripts/miscellaneous/preprocess_conekt.git

'''

## 2. Install and set up the virtual environment

In the folder you created, install and configure the virtual environment, Be patient, as this installation may take a few minutes.

'''bash

conda env create -n conekt-grasses-snakemake-pipeline -f environment.yaml

'''

Once the installation is complete, activate the environment:

'''bash

conda activate conekt-grasses-snakemake-pipeline

'''

## 3. Configure software paths in config.yaml

Before running pipeline, review the config.yaml file. Some paths ind the configuration are user-specific, while others are cluster-specific. Therefore, whenever a new user intends to run the pipeline, the software paths must bve adjusted accordingly.

## 4. Configure the Snakefile

In the file, you will need to adjust the name of yours samples and the reference transcriptome.

## 4. Run the pipeline

Start with a test run to ensure everything is set up correctly:

'''bash

snakemake -np

'''

This command will lst all planned steps, from downloading raw reads to generating quantification matrices and reports.

If everything looks correct, execute pipeline:

'''bash

qsub Snakefile.sh

'''

