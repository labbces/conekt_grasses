# CoNekT Grasses

> A web platform for the exploration and analysis of gene expression and co-expression networks in grass species.

CoNekT Grasses enables researchers to integrate, visualize, and interpret large-scale transcriptomic datasets in an intuitive and efficient way. It is based on [CoNekT](https://doi.org/10.1093/nar/gky336) (Proost et al., 2018), an open-source web server dedicated to the analysis of gene expression data.

---

## Table of Contents

- [Overview](#overview)
- [System Requirements](#system-requirements)
- [Installation](#installation)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. CoNekT Virtual Environment](#2-conekt-virtual-environment)
  - [3. Populate Virtual Environment](#3-populate-virtual-environment)
- [Database Configuration](#database-configuration)
- [Data Preparation](#data-preparation)
  - [Data directory structure](#data-directory-structure)
  - [Configuring the pipeline script](#configuring-the-pipeline-script)
  - [info_species.tsv](#info_speciestsv)
  - [Expression annotation file](#expression-annotation-file)
- [Running the Pipeline](#running-the-pipeline)
- [Monitoring the Pipeline](#monitoring-the-pipeline)
- [Adding New Data](#adding-new-data)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Team](#team)
- [Licenses](#licenses)

---

## Overview

CoNekT Grasses is designed for bioinformaticians and plant researchers working with grass species transcriptomics. It provides:

- Integration of large-scale RNA-seq datasets
- Gene co-expression network analysis
- Expression specificity calculation
- Interactive visualization via a web interface

---

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Linux (Ubuntu tested) | Ubuntu 20.04+ |
| RAM | 16 GB | 32–64 GB |
| Disk | 20 GB | Tens of GB |
| Python | 3.8 | 3.8 |
| Other | Git, MariaDB | — |
| Permissions | `sudo` access or machine administrator | — |

---

## Installation

### 1. Clone the Repository

Create a working directory and clone the repository:

```bash
mkdir CoNekT && cd CoNekT
git clone https://github.com/labbces/conekt_grasses.git
```

### 2. CoNekT Virtual Environment

Install Python 3.8 (if not already available):

```bash
cd CoNekT/
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.8
```

Install dependencies and set up the environment:

```bash
sudo apt install python3.8-venv python3.8-dev
python3.8 -m ensurepip --default-pip
python3.8 -m pip install --upgrade pip setuptools wheel

python3.8 -m venv conekt
source conekt/bin/activate

sudo apt-get install python3.8-dev libmysqlclient-dev apache2 apache2-dev libapache2-mod-wsgi-py3
pip3 install -r requirements.txt
```

### 3. Populate Virtual Environment

Deactivate the current environment and go to the scripts directory:

```bash
deactivate
cd scripts/
```

Check your system Python version:

```bash
python3 --version
```

Create and activate the populate environment (adjust the version below to match your system):

```bash
sudo apt install python3.12-venv        # replace 3.12 with your version
python3 -m venv populate_conekt
source populate_conekt/bin/activate
pip install -r requirements.txt
```

Create the credentials file `scripts/mariadb_credentials.txt`:

```text
DB_ADMIN=conekt_grasses_admin
DB_NAME=conekt_grasses_db
DB_PASSWORD=YOUR_DB_PASSWORD
```

> ⚠️ **Security:** Never commit this file to version control. Add `mariadb_credentials.txt` to your `.gitignore`.

Now that you have cloned the repository, created both virtual environments, and added the necessary files, your repository structure should look like this:

```
CoNekT/                              # Repository root (created by git clone)
├── artwork/                         # Logos and visual assets
├── bin/                             # CoNekT virtual environment binaries
├── conekt/                          # Main Flask application
│   ├── app.py
│   ├── controllers/                 # Route controllers
│   ├── models/                      # Database models
│   ├── templates/                   # HTML templates
│   └── static/                      # Static assets
├── CoNekT/                          # CoNekT virtual environment (lib, include, etc.)
├── scripts/                         # Population scripts
│   ├── populate_conekt_grasses.sh   # Main pipeline script
│   ├── validate_input_data.sh       # Input data validation
│   ├── mariadb_credentials.txt      # DB credentials (NOT committed)
│   ├── requirements.txt
│   ├── add/                         # Scripts for adding new data
│   └── Populate_CoNekT/             # Populate virtual environment
├── tests/                           # Test suite
│   └── data/                        # Example input files (useful as reference)
│       ├── expression/
│       ├── functional_data/
│       └── ontology/
├── utils/                           # Utility modules
├── config.py                        # Your local configuration (NOT committed)
├── config.template.py               # Configuration template
├── run.py
├── requirements.txt
├── LICENSE
└── LICENSE_CoNekT.md
```

> 💡 **Tip:** The `tests/data/` directory contains small example input files that are useful as formatting references when preparing your own data.

---

## Database Configuration

### 1. Create the Flask configuration file

```bash
cd conekt_grasses/CoNekT/
cp config.template.py config.py
```

Edit `config.py` to set your database URI, secret key, and admin password:

```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://conekt_grasses_admin:YOUR_DB_PASSWORD@localhost/conekt_grasses_db'
SECRET_KEY = 'your-secret-key-here'   # change this!
ADMIN_PASSWORD = 'your-admin-password' # change this!
```

### 2. Set up MariaDB

Open MariaDB as root:

```bash
sudo mariadb
```

And run:

```sql
CREATE USER conekt_grasses_admin@localhost IDENTIFIED BY 'YOUR_DB_PASSWORD';

CREATE DATABASE conekt_grasses_db CHARACTER SET latin1 COLLATE latin1_general_ci;

GRANT INDEX, CREATE, DROP, SELECT, UPDATE, DELETE, ALTER, EXECUTE, INSERT
  ON conekt_grasses_db.* TO conekt_grasses_admin@localhost;

GRANT FILE ON *.* TO conekt_grasses_admin@localhost;
```

> **Note:** The `latin1` character set is required — `utf8mb4` (MariaDB default) is not compatible with sqlalchemy-migrate.

### 3. Increase the max allowed packet size

```bash
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

Add or uncomment the following line:

```ini
max_allowed_packet = 512M
```

Restart MariaDB and verify:

```bash
sudo systemctl restart mariadb
mariadb -u conekt_grasses_admin -p -e "SHOW VARIABLES LIKE 'max_allowed_packet';"
# Expected output: 536870912
```

### 4. Initialize the database

```bash
cd conekt_grasses/CoNekT/
source conekt/bin/activate
export FLASK_APP=run.py
flask initdb
flask db init
```

### 5. Start the web application

```bash
flask run
```

> **Note:** Running the web application is **not required** for data population. You can proceed directly to [Data Preparation](#data-preparation) and [Running the Pipeline](#running-the-pipeline). Once the pipeline completes, start the application to explore and verify how the data was loaded into the platform.

---

## Data Preparation

Before running the pipeline, you need to organize your input data in a dedicated directory **outside** the repository and configure the pipeline script accordingly.

### Data directory structure

The path to this directory is defined by the `DATA_DIR` variable in `populate_conekt_grasses.sh`. The expected structure is:

```
conekt_dados/
├── BLAST/
│   ├── BLASTn/
│   │   └── AllCDS.fasta                        # BLAST nucleotide database
│   └── BLASTp/
│       └── AllProteins.fasta                   # BLAST protein database
├── ComparativeGenomics/
│   └── Orthogroups.txt                         # Gene families (e.g., from OrthoFinder)
├── FunctionalData/
│   ├── interpro.xml                            # InterPro database (XML)
│   ├── go.obo                                  # Gene Ontology (OBO format)
│   └── CAZyDB.08062022.fam-activities.txt      # CAZy database
├── Ontology/
│   ├── plant-ontology.txt                      # Plant Ontology (PO)
│   └── peco.tsv                                # Plant Experimental Conditions Ontology (PECO)
└── Species/
    ├── info_species.tsv                        # Species metadata table
    └── <SPECIES_CODE>/                         # One directory per species (e.g., Scp1, Osa, Zma)
        ├── <CODE>_cds.fa                       # CDS sequences (FASTA)
        ├── <CODE>_rnas.fa                      # RNA sequences (FASTA)
        ├── <CODE>_cds_description.txt          # Gene descriptions
        ├── <CODE>_interproscan.tsv             # InterProScan results (.tsv or .tsv.gz)
        ├── <CODE>_go.txt                       # GO annotations
        ├── <CODE>_cazymes.txt                  # CAZyme annotations
        ├── <CODE>_expression_matrix.txt        # TPM expression matrix
        └── <CODE>_expression_annotation.txt    # Sample annotation file
```

> ⚠️ **Important:** File names must follow the `<SPECIES_CODE>_<filetype>` convention exactly, replacing `<SPECIES_CODE>` with the code defined in `SPECIES_ARRAY` and `info_species.tsv` (e.g., `Scp1_expression_matrix.txt`). The pipeline locates files by constructing paths from these codes — any mismatch will cause the step to be skipped or fail.

### Configuring the pipeline script

Edit `populate_conekt_grasses.sh` and set the following variables to match your environment:

```bash
BASE_DIR="${HOME}/path/to/conekt_grasses"     # Root of the cloned repository
SCRIPTS_DIR="$BASE_DIR/CoNekT/scripts"
DATA_DIR="${HOME}/path/to/conekt_dados/v0.3"  # Root of your data directory
SPECIES_ARRAY=("Scp1")                        # Species codes to process
```

### info_species.tsv

This file, located at `DATA_DIR/Species/info_species.tsv`, provides metadata for each species to be loaded. It has **7 tab-separated columns** and supports comments with `#`. Example:

```tsv
#Species_name                   Code    Source      Genome_Transcriptome_version    DOI                  CDS_file                                          RNA_file
Sugarcane pan-transcriptome v1  Scp1    LabBCES     Scp1                                                 /home/user/conekt_dados/Species/Scp1/Scp1_cds.fa  /home/user/conekt_dados/Species/Scp1/Scp1_rnas.fa
Oryza sativa                    Osa     Phytozome   Osativa_v7_0                    10.1093/nar/gkl976   /home/user/conekt_dados/Species/Osa/Osa_cds.fa    /home/user/conekt_dados/Species/Osa/Osa_rnas.fa
```

| Column | Description |
|--------|-------------|
| `Species_name` | Full species name or assembly description |
| `Code` | Short species code used throughout the pipeline (e.g., `Scp1`) |
| `Source` | Origin of the genome/transcriptome (e.g., Phytozome, LabBCES) |
| `Genome_Transcriptome_version` | Version identifier of the assembly |
| `DOI` | Publication DOI (optional, can be left empty) |
| `CDS_file` | Absolute path to the CDS FASTA file |
| `RNA_file` | Absolute path to the RNA FASTA file |

> ⚠️ **Important:** The species code (`Code` column) must be **identical** in the directory name under `Species/`, in `SPECIES_ARRAY`, and in this file. Lines starting with `#` are treated as comments and ignored by the pipeline.

### Expression annotation file

The file `<CODE>_expression_annotation.txt` describes each RNA-seq sample used in the expression matrix. It must have **exactly 9 tab-separated columns** with the following header:

```
SampleID	DOI	ConditionDescription	Replicate	Strandness	Layout	PO_anatomy	PO_dev_stage	PECO
```

Example rows:

```tsv
SampleID        DOI                     ConditionDescription    Replicate   Strandness       Layout      PO_anatomy   PO_dev_stage  PECO
SRR768594       10.1038/nbt.3019        Segment 01              1           unstranded       single-end  PO:0025034
SRR17151210     10.1111/jipb.13357      cold stress - 2h        3           strand specific  paired-end  PO:0025034
SRR15993148     10.1038/s42003-021...   Zax2_+P_Sh_24hr         1           strand specific  paired-end  PO:0025297
```

| Column | Description | Required |
|--------|-------------|----------|
| `SampleID` | SRA run accession or any unique sample identifier | ✅ |
| `DOI` | Publication DOI for the dataset | ✅ |
| `ConditionDescription` | Free-text description of the experimental condition | ✅ |
| `Replicate` | Replicate number — **must be an integer** (1, 2, 3...) | ✅ |
| `Strandness` | Library strandness: `unstranded` or `strand specific` | ✅ |
| `Layout` | Sequencing layout: `single-end` or `paired-end` | ✅ |
| `PO_anatomy` | Plant Ontology term for the tissue/anatomy (e.g., `PO:0025034`) | ⚠️ recommended |
| `PO_dev_stage` | Plant Ontology term for the developmental stage | ⚠️ recommended |
| `PECO` | Plant Experimental Conditions Ontology term | ⚠️ recommended |

> ⚠️ **Critical:** The `Replicate` column must contain **only integers** (1, 2, 3...). Using letters (e.g., A, B, C) or any non-integer value will cause the pipeline to fail at the expression data loading step.

> 💡 **Tip:** The ontology columns (`PO_anatomy`, `PO_dev_stage`, `PECO`) can be left empty, but filling them in enables the expression specificity features of the platform.

---

## Running the Pipeline

Navigate to the scripts directory and execute:

```bash
cd scripts/
./populate_conekt_grasses.sh
```

A successful run ends with:

```
Pipeline completed successfully!
```

### Runtime estimates

| Species | Estimated time |
|---------|----------------|
| Sugarcane (`Scp1`) | 24–72 hours |

> ⚠️ **Do not interrupt the specificity calculation step** — it is the most computationally intensive part of the pipeline.

### Optional steps

Some pipeline steps (e.g., co-expression networks, clustering) are **commented out by default** because they require specific input data that may not always be available. Enable or disable steps by commenting/uncommenting the corresponding sections in the script. Make sure all required input files are in place before enabling a step.

---

## Monitoring the Pipeline

Monitor system resources during a long run:

```bash
htop
# or
watch -n 2 free -h
```

Example progress messages:

```
→ Processed 10000 profiles
→ Committed 400 specificities
```

---

## Adding New Data

Scripts for adding data are located in `scripts/add/`.

### Add more expression profiles for an existing species

```bash
python add/add_expression_data.py --species_code Scp1 [other options]
```

### Add a new species

Run the following scripts in order:

| Step | Script |
|------|--------|
| 1 | `add_species.py` |
| 2 | `add_gene_descriptions.py` |
| 3 | `add_interproscan.py` |
| 4 | `add_go.py` |
| 5 | `add_cazymes.py` |
| 6 | `add_expression_data.py` |
| 7 (optional) | `calculate_specificities_fast.py` |
| 8 | `update_counts.py` |

---

## Documentation

Build the HTML documentation with Sphinx:

```bash
cd conekt_grasses/
source conekt/bin/activate
cd docs/
sphinx-build -b html source/ build/
xdg-open build/index.html
```

The project uses the MyST Markdown parser. Make sure `conf.py` contains:

```python
extensions = ["myst_parser"]
```

---

## Troubleshooting

| Problem | Likely cause | Solution |
|---------|-------------|----------|
| `max_allowed_packet` error | Packet size too small | Set `max_allowed_packet = 512M` in MariaDB config |
| `Replicate` column error | Non-integer values in annotation file | Use only integers (1, 2, 3) in the `Replicate` column |
| Pipeline hangs at specificity step | Large dataset / insufficient RAM | Use a machine with 32–64 GB RAM; do not interrupt |
| Species not found | Name mismatch | Ensure species code matches in directory, `SPECIES_ARRAY`, and `info_species.tsv` |
| Database character set error | Wrong collation | Use `latin1_general_ci` — not `utf8mb4` |
| Flask app not starting | Missing config | Check `config.py` exists and has valid DB URI |

---

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

Please make sure your changes are tested and that no credentials or local paths are included in commits.

---

## Team

### Developers

- Dr. Renato Augusto Correa dos Santos
- Prof. Dr. Diego M. Riaño-Pachón *(group leader)*

### Collaborators

- Felipe Vaz Peres
- Jorge Muñoz

### Previous Collaborators

- David Texeira Ferraz
- Bianca Santos Pastos
- Arthur Shuzo Owtake Cardoso

---

## Licenses

- [LabBCES LICENSE](LICENSE)
- [Original CoNekT license — Dr. Sebastian Proost](LICENSE_CoNekT.md)