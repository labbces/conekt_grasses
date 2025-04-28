# CoNekT Grasses Data Population Guide

## Prerequisites
Before populating CoNekT Grasses, you must initialize the MariaDB database to ensure that the necessary table structures are created. Follow the instructions in the `connect_mysql.md` file up to the "Running the database migrations" step.

## Setting Up the Virtual Environment
CoNekT requires a separate Python virtual environment for data population due to differences in Python versions. To create and activate the `Populate_CoNekT` virtual environment, execute the following commands:

```bash
deactivate  # Deactivate any existing virtual environment
cd CoNekT/scripts/
virtualenv --python=python3.10 Populate_CoNekT
source Populate_CoNekT/bin/activate
```

Now that the environment is active, we will install the necessary requirements:

```bash
pip install -r requirements.txt
```

## Running the Population Scripts
After activating the virtual environment, navigate to the `add` directory to execute the necessary scripts for populating CoNekT with your data.

For additional script options and requirements, use the help (-h) command.

### 1. Adding Ontology Data
Before inserting other data, start by adding general ontology data using the `add_ontologies.py` script. This step incorporates:
- **Plant Ontology (PO)**
- **Plant Experimental Conditions Ontology (PECO)**

These ontologies need to be inserted only once unless an update is required.

```bash
python3 add_ontologies.py --plant_ontology ../../../../datatest/plant-ontology.txt --plant_e_c_ontology ../../../../datatest/peco.tsv --db_admin conekt_grasses_admin --db_name conekt_grasses_db
```
### 2. Adding Functional Data
Next, use the `add_functional_data.py` script to add functional data. This step requires:
- **InterPro** (GO format: `go.obo`)
- **CAZyme Database** (TXT format)
- **Gene Ontology Files** (`go.obo` format)

It is not necessary to insert all three files at the same time. If any of these datasets have already been added, you may insert the remaining ones separately.

```bash
python3 add_functional_data.py --interpro_xml ../../../../datatest/interpro.xml/interpro.xml --gene_ontology_obo ../../../../datatest/go.obo --cazyme ../../../../datatest/CAZyDB.08062022.fam-activities.txt --db_admin conekt_grasses_admin --db_name conekt_grasses_db
```

*Observation: In this script, if you insert one of the files incorectly, you must delete the wrong files from the database. If you put incorrect information about the file's path, then you may add only the arguments of those files, otherwise you will experience an overlap error.*

### 3. Adding Species Information
To add species data, first create a tab-separated values (TSV) or TXT file containing the following columns (if you would like to add a header, please comment it's line):

- `Species_name`
- `Code`
- `Source`
- `Genome_Transcriptome_version`
- `DOI`
- `CDS_file`
- `RNA_file`

Then, proceed with adding functional information for the species using the following scripts:

- `add_cazymes.py`
	```bash
	python3 add_cazymes.py --cazyme_tsv ../../../../datatest/sorghum/Sbi_cazymes.txt --species_code Sbi --db_admin conekt_grasses_admin --db_name conekt_grasses_db
	```
	
- `add_go.py`
	```bash
	python3 add_go.py --go_tsv ../../../../datatest/sorghum/Sbi_go.txt --species_code Sbi --annotation_source ../../../../datatest/sorghum/Sbi_interproscan.tsv --db_admin conekt_grasses_admin --db_name conekt_grasses_db
	```
	
- `add_interproscan.py`
	```bash
	python3 add_interproscan.py --interproscan_tsv ../../../../datatest/sorghum/Sbi_interproscan.tsv --species_code Sbi --db_admin conekt_grasses_admin --db_name conekt_grasses_db
	```

At this stage, data is structured specifically for the species being added.

### 4. Adding Species Data
Further species-related information can be added using these scripts:

- `add_gene_description.py`
	```bash
	python3 add_gene_descriptions.py --species_code Sbi --gene_description ../../../../datatest/sorghum/Sbi_cds_description.txt --db_admin conekt_grasses_admin --db_name conekt_grasses_db
	```
	
- `add_gene_families.py`
	```bash
	python3 add_gene_families.py --orthogroups ../../../../datatest/Orthogroups.txt --description OrthoFinder2_CoNekTv0.3_sbi --db_admin conekt_grasses_admin --db_name conekt_grasses_db
	```
	
- `add_gene_trees.py`
	(command example)

### 5. Adding Expression and Network Data
Finally, integrate expression and network data using:

- `add_expression_data.py`
	```bash
	python3 add_gene_descriptions.py --species_code Sbi --gene_descriptions ../../../../datatest/sorghum/Sbi_cds_description.txt --db_admin conekt_grasses_admin --db_name conekt_grasses_db
	```
	
- `add_network.py`
	```bash
	python3 add_network.py --network ../../../../datatest/sorghum/Sbi_network_v0_2_Xmeeting.txt --species_code Sbi --hrr_score_threshold 30 --description Sorghum_bicolor_coexpression_network_v02_X_meeting_2023 --db_admin conekt_grasses_admin --db_name conekt_grasses_db
	```

By following these steps, you will successfully populate CoNekT Grasses with the necessary data for further analysis.
