# CoNekT Grasses

## What is CoNekT Grasses?

CoNekT Grasses derives from CoNekT, described in Proost *et al*. 2018. ( [https://doi.org/10.1093/nar/gky336](https://doi.org/10.1093/nar/gky336) )

# Tutorial

## CoNekT Grasses Installation and Database Population

## Overview

CoNekT Grasses is a platform for exploring gene expression networks in grass species.
This tutorial describes how to install the system and populate the database with expression data.

---

## 1. System Requirements

Before starting, make sure your system has the following installed:

* Linux (tested on Ubuntu)
* Python 3
* Git
* MariaDB

For large datasets it is recommended to have:

* **32–64 GB RAM**
* **Tens of GB of disk space**

---

## 2. Environment Setup

1. Create a directory for CoNekT.

2. Clone the repository from GitHub into the directory you created:

```bash
git clone https://github.com/labbces/conekt_grasses.git
```

3. Create the **CoNekT** virtual environment by following the instructions in:

https://github.com/labbces/conekt_grasses/blob/working_install/README.md#quick-start-for-developers

4. Create the **Populate** virtual environment as described in:

https://github.com/labbces/conekt_grasses/blob/main/CoNekT/scripts/README_populate.md#setting-up-the-virtual-environment

---

## 3. Database Configuration

1. Follow the instructions below to create the database:

https://github.com/labbces/conekt_grasses/blob/main/CoNekT/docs/source/connect_mysql.md

2. Edit the MariaDB configuration file:

```bash
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

3. Uncomment or add the following line:

```ini
max_allowed_packet = 512M
```

4. Restart MariaDB:

```bash
sudo systemctl restart mariadb
```

5. Verify the configuration:

```sql
SHOW VARIABLES LIKE 'max_allowed_packet';
```

Expected value:

```
536870912
```

---

## 4. Data Organization

1. In the script `populate_conekt_grasses.sh`, modify the following variables:

* `BASE_DIR`
* `SCRIPTS_DIR`
* `DATA_DIR`
* `SPECIES_ARRAY` (add the species you want, e.g., `Scp1`)

2. Prepare the file `info_species.tsv` with the path to your data:

```
species_code    data_path
Scp1            /home/your_user/data/Scp1
```

**Important:**
The species name must match in:

* the data directory
* the `SPECIES_ARRAY` variable
* the `info_species.tsv` file

3. **Check the annotation file (`expression_annotation.txt`):**

* It must contain **9 tab-separated columns**
* The `Replicate` column must contain **only integers** (1, 2, 3...), **never letters** (B, M, P...)

---

## 5. Running the Pipeline

Navigate to:

```
CoNekT/scripts
```

Run the pipeline:

```bash
./populate_conekt_grasses.sh
```

If everything runs correctly, you should see:

```
Pipeline completed successfully!
```

**Important**

For sugarcane (`Scp1`), the pipeline may take **24–72 hours**, depending on the hardware.

The **specificity calculation** step is the most computationally intensive — do not interrupt it.

---

## 6. Monitoring the Pipeline

You can monitor system resources using:

```bash
htop
```

or

```bash
watch -n 2 free -h
```

Progress messages may look like:

```
→ Processed 10000 profiles
→ Committed 400 specificities
```

---

## 7. Adding New Data

Scripts are located in:

```
CoNekT/scripts/add
```

### Adding more expression profiles for the same species

```bash
python add/add_expression_data.py --species_code Scp1 ...
```

### Adding a new species

Run the following scripts:

* `add_species.py`
* `add_gene_descriptions.py`
* `add_interproscan.py`
* `add_go.py`
* `add_cazymes.py`
* `add_expression_data.py`
* (optional) `calculate_specificities_fast.py`
* `update_counts.py`

 

## Quick Start for developers

CoNekT Grasses currently requires:
 * Python 3.8

To install Python 3.8 execute the following codes:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.8
```

Dependencies are usually installed using `apt` and `pip`:


```bash
apt install python3.8-venv python3.8-dev
python3.8 -m ensurepip --default-pip
python3.8 -m pip install --upgrade pip setuptools wheel
pip3.8 install virtualenv
```

To set up the environment from the root directory of the repository, run:

```bash
virtualenv --python=python3.8 CoNekT
source CoNekT/bin/activate
sudo apt-get install python3.8-dev libmysqlclient-dev apache2 apache2-dev libapache2-mod-wsgi-py3
pip install -r requirements.txt
```

Next steps:

 * [Running tests](https://github.com/labbces/conekt_grasses/blob/main/CoNekT/docs/source/run_tests.md)
 * [Build the datatase](https://github.com/labbces/conekt_grasses/blob/main/CoNekT/docs/source/connect_mysql.md)
 * [Add data to CoNekT Grasses](https://github.com/labbces/conekt_grasses/blob/main/CoNekT/docs/source/building_conekt.md)

## Building documentation with Sphinx


Documentation can be generated using Sphinx.

To generate the documentation, run:

```bash
cd CoNekT/docs/
sphinx-build -b html source/ build/
```

Note that we changed the default Sphinx builder to use the Markdown parser. This is done by adding the following line to `conf.py` file in the `CoNekT/docs` folder:

```
extensions = ["myst_parser"]
```


## Developers

 * Dr. Renato Augusto Correa dos Santos
 * Prof. Dr. Diego M. Riaño-Pachón (group leader)


## Collaborators

 * Felipe Vaz Peres
 * Jorge Muñoz


## Previous collaborators

 * David Texeira Ferraz
 * Bianca Santos Pastos
 * Arthur Shuzo Owtake Cardoso


## Licenses

 * [LabBCES LICENSE](LICENSE)
 * [Original CoNekT license (Dr. Sebastian Proost)](LICENSE_CoNekT.md)
