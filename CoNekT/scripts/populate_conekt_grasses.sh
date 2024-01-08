#!/usr/bin/env bash

BASE_DIR=/media/renato/SSD1TB/Repositories/conekt_grasses
SCRIPTS_DIR=$BASE_DIR/CoNekT/scripts
TEST_DATA_DIR=$BASE_DIR/CoNekT/tests/data

DB_ADMIN=conekt_grasses_admin_test_ipr
DB_NAME=conekt_grasses_db_test_ipr
DB_PASSWORD="E,~5*;{9f{p2VGp^"
export FLASK_APP=run.py

cd $BASE_DIR/CoNekT
source bin/activate
flask initdb
if [ -d $BASE_DIR/CoNekT/migrations ]; then
  rm -fr $BASE_DIR/CoNekT/migrations
fi
flask db init

# Deactivate virtual environment
# Currently it is necessary because libraries in the virtual environment
# are not compatible with the libraries in the system used by the scripts
deactivate

echo "Populating CoNekT Grasses with functional data"
$SCRIPTS_DIR/add/add_functional_data.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --interpro_xml $TEST_DATA_DIR/test_interpro.xml\
 --gene_ontology_obo $TEST_DATA_DIR/test_go.obo\
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with ontology data"
$SCRIPTS_DIR/add/add_ontologies.py --plant_ontology $TEST_DATA_DIR/ontology/test.po_table.txt\
 --plant_e_c_ontology $TEST_DATA_DIR/ontology/test.peco_table.txt\
 --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with species data"
$SCRIPTS_DIR/add/add_species.py --input_table $TEST_DATA_DIR/species_info.txt\
 --db_admin $DB_ADMIN \
 --db_name $DB_NAME \
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with gene descriptions"
# Test species 1
$SCRIPTS_DIR/add/add_gene_descriptions.py --species_code Sp1\
 --gene_descriptions $TEST_DATA_DIR/test.descriptions.txt\
 --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD

# Test species 2
$SCRIPTS_DIR/add/add_gene_descriptions.py --species_code Sp2\
 --gene_descriptions $TEST_DATA_DIR/test2.descriptions.txt\
 --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with functional annotation data"
# Test species 1
$SCRIPTS_DIR/add/add_interproscan.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --interproscan_tsv $TEST_DATA_DIR/functional_data/test.interpro.txt\
 --species_code Sp1

# Test species 2
$SCRIPTS_DIR/add/add_interproscan.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --interproscan_tsv $TEST_DATA_DIR/functional_data/test2.interpro.txt\
 --species_code Sp2

echo "Populating CoNekT Grasses with expression profiles"
# Test species 1
$SCRIPTS_DIR/add/add_expression_data.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code Sp1\
 --expression_matrix $TEST_DATA_DIR/expression/test.tpm.matrix.txt\
 --sample_annotation $TEST_DATA_DIR/expression/test.expression_annotation.txt

# Test species 2
$SCRIPTS_DIR/add/add_expression_data.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code Sp2\
 --expression_matrix $TEST_DATA_DIR/expression/test2.tpm.matrix.txt\
 --sample_annotation $TEST_DATA_DIR/expression/test2.expression_annotation.txt

echo "Populating CoNekT Grasses with expression specificities"
# Test species 1
$SCRIPTS_DIR/build/calculate_specificities.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code Sp1

# Test species 2
$SCRIPTS_DIR/build/calculate_specificities.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code Sp2

echo "Update all counts in the database"
$SCRIPTS_DIR/build/update_counts.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD 