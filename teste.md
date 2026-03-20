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
- [Data Organization](#data-organization)
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

---

## Installation

### 1. Clone the Repository

Create a working directory and clone the repository:

```bash
mkdir CoNekT && cd CoNekT
git clone https://github.com/labbces/conekt_grasses.git
cd conekt_grasses
```

### 2. CoNekT Virtual Environment

Install Python 3.8 (if not already available):

```bash
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

---

## Database Configuration

### 1. Create the Flask configuration file

```bash
cd conekt_grasses/
cp config.template.py config.py
```

Edit `config.py` to set your database URI, secret key, and admin password:

```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://conekt_grasses_admin:YOUR_DB_PASSWORD@localhost/conekt_grasses_db'
SECRET_KEY = 'your-secret-key-here'   # change this!
ADMIN_PASSWORD = 'your-admin-password' # change this!
```

### 2. Set up MariaDB

Connect as root and run:

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
export FLASK_APP=run.py
flask initdb
flask db init
```

### 5. Start the web application

```bash
flask run
```

---

## Data Organization

### Project directory structure

```
CoNekT/
├── conekt_grasses/         # Main application
│   ├── config.py           # Your local configuration (not committed)
│   ├── config.template.py  # Configuration template
│   └── scripts/
│       ├── populate_conekt_grasses.sh
│       ├── mariadb_credentials.txt   # Not committed
│       ├── info_species.tsv
│       └── add/            # Scripts for adding new data
└── data/
    └── Scp1/               # Species-specific data directory
```

### Configuring the pipeline script

Edit `populate_conekt_grasses.sh` and set the following variables:

```bash
BASE_DIR="/path/to/CoNekT"
SCRIPTS_DIR="$BASE_DIR/conekt_grasses/scripts"
DATA_DIR="/path/to/data"
SPECIES_ARRAY=("Scp1")      # Add your species codes here
```

### info_species.tsv

```tsv
species_code	data_path
Scp1	/home/your_user/data/Scp1
```

> ⚠️ **Important:** The species code must be **identical** in the data directory name, `SPECIES_ARRAY`, and `info_species.tsv`.

### Expression annotation file

The file `expression_annotation.txt` must have **exactly 9 tab-separated columns**.  
The `Replicate` column must contain **only integers** (e.g., 1, 2, 3) — letters are not accepted (e.g., B, M, P will cause errors).

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