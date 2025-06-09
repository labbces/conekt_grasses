# Conekt Grasses – Snakemake Pipeline

This repository contains the snakemake pipeline for reproducing the analysis of the Conekt Grasses dataset - from raw data to gene expression matrices and reports.

> [!TIP]
> Follow this step-by-step tutorial to setup and run the pipeline


## 1. Clone this repository

Create a folder with the name of the project/species you are working on:
```bash
# creating the sugarcane repository in your home inside /Storage/data1/${USER}
cd /Storage/data1/${USER}
mkdir sugarcane
```

> [!WARNING]
> By default, the global variable `$USER` holds you username in the system  
> You can always check if it is corret with this command: `echo ${USER}`  
> This should print your username in the screen 

Inside the folder you created, clone this github repository: 

```bash
# enter in sugarcane directory
cd sugarcane

# clone this repository
git clone https://github.com/labbces/conekt_grasses.git
```

## 2. Install and set up the virtual environment

In the folder you cloned, move to `preprocess_conekt` directory:

```bash
# moving to preprocess_conekt
cd conekt_grasses/CoNekT/scripts/miscellaneous/preprocess_conekt
```


Be patient, as this installation may take a few minutes.

> [!IMPORTANT]
> If you are using a cluster with the `module` tool management, you will first have to load conda:

```bash
# load miniconda
module load miniconda3

# now you can install the conda environment
conda env create -n conekt-grasses-snakemake-pipeline -f environment.yaml
```

Once the installation is complete, activate the environment:

```bash
# activating the environment
conda activate conekt-grasses-snakemake-pipeline
```

> [!TIP]
> After activating the environment, your terminal will show the following: `(conekt-grasses-snakemake-pipeline) ${USER}@frontend`
> This means that the env `conekt-grasses-snakemake-pipeline` is activated!

## 3. Configure software paths in config.yaml

Before running pipeline, review the [config.yaml](https://github.com/labbces/conekt_grasses/blob/documentation-review/CoNekT/scripts/miscellaneous/preprocess_conekt/config.yaml) file.  
Some paths in the configuration are user-specific, while others are cluster-specific. Therefore, whenever a new user intends to run the pipeline, the software paths must be adjusted accordingly.

## 4. Adjust the Snakefile for proper inputs

In the file [Snakefile](https://github.com/labbces/conekt_grasses/blob/documentation-review/CoNekT/scripts/miscellaneous/preprocess_conekt/Snakefile), you will need to adjust the name of the CSV file with your samples (SRRs) and the reference transcriptome. Além disso também ajustar a variável read_prefix com o prefixo do nome das corridas de sequenciamento.  
See the example below:

```bash
GENOTYPE='Sugarcane'
SEQTYPE='PAIRED'
read_prefix='@SRR'
samples = pd.read_csv(GENOTYPE+'_samples.csv')
reference_transcriptome = "Scp1_rnas.fa"
```

> [!WARNING]
> You just need to change the `GENOTYPE` and `reference_transcriptome` to match your specie and reference transcriptome.  
> Do not change anything other than these two variables.  

## 5. Run the pipeline

### 5.1 Running your first test!

Start with a dry-run to make sure everything is set up correctly:
```bash
snakemake -np
```

>[!NOTE]
>This will list all planned steps in your terminal, from downloading raw reads to generating quantification matrices and reports.

Once it looks good, you can proceed for the next step!

### 5.2 Run the complete pipeline

The complete pipeline include the following rules: `download_fastq`, `bbduk`, `count_raw_sequences`, `salmon_index`, `salmon_quant`, `count_trimmed_sequences`, `filter_stranded`, `filter_low_mapping_reads`, `preliminar_report`, `merge_quantification_results`.

To run all these rules, you just need to submit [Snakefile.sh](https://github.com/labbces/conekt_grasses/blob/documentation-review/CoNekT/scripts/miscellaneous/preprocess_conekt/Snakefile.sh) to the queue:

```bash
qsub Snakefile.sh
```

### 5.3 Run the pipeline if previously downloaded FASTQ files

If you have your desired fastq files, e.g. after a manual download, you don't need to change anything!  
You just need to move the manually downloaded files to the path that snakemake expect:

```bash
# let's suppose you are in the preprocess_conekt directory and you manually downloaded some fastq files to the data directory

# pwd -> you are here!
/Storage/data1/${USER}/sugarcane/conekt_grasses/CoNekT/scripts/miscellaneous/preprocess_conekt

# you created the "data" directory and downloaded some fastq files
ls data/
SRR7771987_1.fastq  SRR7771990_1.fastq  SRR7771991_1.fastq
SRR7771987_2.fastq  SRR7771990_2.fastq  SRR7771991_2.fastq

# you have to move these files to the path that snakemake expect (in this case, the path is dataset_Sugarcane/1_raw_reads_in_fastq_format)

# let's create and move to this path 
mkdir dataset_Sugarcane && cd dataset_Sugarcane && mkdir 1_raw_reads_in_fastq_format && cd 1_raw_reads_in_fastq_format

# now you are inside 1_raw_reads_in_fastq_format, take a look:
pwd
/Storage/data1/${USER}/sugarcane/conekt_grasses/CoNekT/scripts/miscellaneous/preprocess_conekt/dataset_Sugarcane/1_raw_reads_in_fastq_format/

# you just have to move the downloaded fastq files here!
mv ../../data/* . 
```

> [!IMPORTANT]
> Remember that you set `GENOTYPE=Sugarcane` in the [Snakefile](https://github.com/labbces/conekt_grasses/blob/documentation-review/CoNekT/scripts/miscellaneous/preprocess_conekt/Snakefile)  
> If you are working with other specie, the expected path to keep the downloaded fastq files will change!  
> The path for the downloaded fastq files must always be `dataset_${GENOTYPE}/1_raw_reads_in_fastq_format/`  

After that, snakemake will notice that you already have downloaded the files and will automaticallyt skip the `download_fastq` rule.  
Let's see that:

```bash
# move again to preprocess_conekt
cd /Storage/data1/${USER}/sugarcane/conekt_grasses/CoNekT/scripts/miscellaneous/preprocess_conekt

# you can do a dry-run and see that snakemake will skip the download rule!
snakemake -np
```

> [!TIP]
> You can run `snakemake -np` and see that the `download_fastq` rule was skipped

### 5.4 Run the pipeline and skip the filter_strand rule 

In some cases, the rule `filter_stranded` isn't working properly.  
For the datasets that we already now the strandness, we can skip this rule using the parameter `--config skip_filter_stranded=true`!

> [!WARNING]
> You ONLY need to run snakemake with this command if you want to skip the `filter_stranded` rule

```bash
# do a dry-run and see snakemake skiping the filter_stranded rule
snakemake -np --config skip_filter_stranded=true

# if everything looks good, you can change the command in the Snakefile.sh

# open and change the Snakefile - you just need to add "--config skip_filter_stranded=true", see below:
snakemake -p -k --resources load=10 -s Snakefile --cluster "qsub -q all.q -V -l h={params.server} -cwd -pe smp {threads}" --jobs 10 --jobname "{rulename}.{jobid}" --use-conda --latency-wait 60 --config skip_filter_stranded=true

# after that, just run the updated Snakefile.sh as before
qsub Snakefile.sh
```
