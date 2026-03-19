🌱 CoNekT Grasses
Overview

CoNekT Grasses is an extension of CoNekT, described in Proost et al. (2018) (https://doi.org/10.1093/nar/gky336
), an interactive and open-source platform for the analysis of gene expression and co-expression networks.

This repository provides tools to install, populate, and manage expression datasets for grasses species, enabling large-scale transcriptomic analysis.

⚡ Quick Start
git clone https://github.com/labbces/conekt_grasses.git
cd conekt_grasses

# Create environment (Python 3.8 required)
python3.8 -m venv conekt_env
source conekt_env/bin/activate

pip install -r requirements.txt

# Run pipeline
cd CoNekT/scripts
./populate_conekt_grasses.sh
🧰 System Requirements
Required

Linux (tested on Ubuntu)

Python 3.8

Git

MariaDB

Recommended (for large datasets)

32–64 GB RAM

Tens of GB of disk space

⚙️ Installation and Environment Setup
1. Clone the repository
git clone https://github.com/labbces/conekt_grasses.git
2. Set up CoNekT environment

Follow the official instructions:

https://github.com/labbces/conekt_grasses/blob/working_install/README.md#quick-start-for-developers

3. Set up Populate environment

Deactivate any active environment:

deactivate

Navigate to scripts directory:

cd CoNekT/scripts/

Check your Python version:

python3 --version

Install the appropriate venv package (example for Python 3.8):

sudo apt install python3.8-venv

Create and activate the environment:

python3.8 -m venv populate_conekt
source populate_conekt/bin/activate

Install dependencies:

pip install -r requirements.txt
4. Configure database credentials

Create the file:

CoNekT/scripts/mariadb_credentials.txt

With the following content:

DB_ADMIN=your_db_user
DB_NAME=your_database_name
DB_PASSWORD=your_secure_password

⚠️ Use a strong password and do not commit this file to version control.

🗄️ Database Configuration

Follow the database setup guide:

https://github.com/labbces/conekt_grasses/blob/main/CoNekT/docs/source/connect_mysql.md

Adjust MariaDB configuration

Edit:

sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf

Add or update:

max_allowed_packet = 512M

Restart MariaDB:

sudo systemctl restart mariadb

Verify:

SHOW VARIABLES LIKE 'max_allowed_packet';

Expected value:

536870912
📁 Data Organization
1. Configure pipeline variables

Edit:

populate_conekt_grasses.sh

Update:

BASE_DIR

SCRIPTS_DIR

DATA_DIR

SPECIES_ARRAY (e.g., Scp1)

2. Prepare species metadata file

Create info_species.tsv:

species_code    data_path
Scp1            /home/your_user/data/Scp1

⚠️ The species code must match:

Directory name

SPECIES_ARRAY

info_species.tsv

3. Validate annotation file

File: expression_annotation.txt

Requirements:

Exactly 9 tab-separated columns

Replicate column must contain only integers (e.g., 1, 2, 3)

▶️ Running the Pipeline
cd CoNekT/scripts
./populate_conekt_grasses.sh

Expected output:

Pipeline completed successfully!
⏱️ Performance Notes

Sugarcane dataset (Scp1) may take 24–72 hours

The specificity calculation step is the most computationally intensive

⚠️ Do not interrupt this step once started

🧩 Optional Pipeline Steps

Some steps (e.g., coexpression networks, clustering) may be commented out by default.

This is intentional.

You may enable or disable steps by editing the script:

# Example: uncomment to enable

✔ Ensure all required input data is properly configured before enabling any step

📊 Monitoring Execution

Monitor system usage with:

htop

or:

watch -n 2 free -h

Example progress output:

→ Processed 10000 profiles
→ Committed 400 specificities
➕ Adding New Data

Scripts available in:

CoNekT/scripts/add
Add expression data to existing species
python add/add_expression_data.py --species_code Scp1 ...
Add a new species

Run the following scripts in order:

add_species.py

add_gene_descriptions.py

add_interproscan.py

add_go.py

add_cazymes.py

add_expression_data.py

(optional) calculate_specificities_fast.py

update_counts.py

👨‍💻 Development Setup
Install Python 3.8
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.8

Install dependencies:

sudo apt install python3.8-venv python3.8-dev
python3.8 -m ensurepip --default-pip
python3.8 -m pip install --upgrade pip setuptools wheel
Create development environment
python3.8 -m venv CoNekT
source CoNekT/bin/activate

sudo apt-get install libmysqlclient-dev apache2 apache2-dev libapache2-mod-wsgi-py3

pip install -r requirements.txt
Next steps

Running tests

Build the database

Add data to CoNekT Grasses

📚 Building Documentation

Generate documentation using Sphinx:

cd CoNekT/
source CoNekT/bin/activate

cd docs/
sphinx-build -b html source/ build/

Open in browser:

xdg-open build/index.html
Markdown support

The documentation uses Markdown via myst_parser.

Ensure the following is set in conf.py:

extensions = ["myst_parser"]
👥 Developers

Dr. Renato Augusto Correa dos Santos

Prof. Dr. Diego M. Riaño-Pachón (Group Leader)

🤝 Collaborators

Felipe Vaz Peres

Jorge Muñoz

🧾 Previous Collaborators

David Teixeira Ferraz

Bianca Santos Pastos

Arthur Shuzo Owtake Cardoso

📄 License

LabBCES LICENSE

Original CoNekT license