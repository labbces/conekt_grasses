#!/usr/bin/env bash

BASE_DIR=/media/renato/SSD1TB/Repositories/conekt_grasses
SCRIPTS_DIR=$BASE_DIR/CoNekT/scripts
TEST_DATA_DIR=/media/renato/Renato_Backup/Projects/CENA/CoNekT_Bioenergy/v0.3

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
 --interpro_xml $TEST_DATA_DIR/FunctionalData/interpro.xml\
 --gene_ontology_obo $TEST_DATA_DIR/FunctionalData/go.obo\
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with ontology data"
# TODO: add PECO data
$SCRIPTS_DIR/add/add_ontologies.py --plant_ontology $TEST_DATA_DIR/Ontology/plant-ontology.txt\
 #--plant_e_c_ontology $TEST_DATA_DIR/ontology/test.peco_table.txt\
 --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with species data"
$SCRIPTS_DIR/add/add_species.py --input_table $TEST_DATA_DIR/info_species_test.tsv\
 --db_admin $DB_ADMIN \
 --db_name conekt_grasses_db_test_ipr \
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with gene descriptions"
for species_code in "Zma" "Osa" "Svi"; do
 $SCRIPTS_DIR/add/add_gene_descriptions.py --species_code "$species_code"\
  --gene_descriptions $TEST_DATA_DIR/Species/"$species_code"/"$species_code"_cds_description.txt\
  --db_admin $DB_ADMIN\
  --db_name $DB_NAME\
  --db_password $DB_PASSWORD
done;

echo "Populating CoNekT Grasses with functional annotation data"
for species_code in "Zma" "Osa" "Svi"; do
 $SCRIPTS_DIR/add/add_interproscan.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --interproscan_tsv $TEST_DATA_DIR/Species/"$species_code"/"$species_code"_interproscan.tsv\
 --species_code "$species_code"
done;

echo "Populating CoNekT Grasses with expression profiles"
# Setaria viridis - inflorescence development
$SCRIPTS_DIR/add/add_expression_data.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code Svi\
 --expression_matrix $TEST_DATA_DIR/Species/Svi/expression/Svi_expression_matrix.txt\
 --sample_annotation $TEST_DATA_DIR/Species/Svi/expression/Svi_expression_annotation.txt

echo "Populating CoNekT Grasses with expression specificities"
# Setaria viridis
$SCRIPTS_DIR/build/calculate_specificities.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code Svi
