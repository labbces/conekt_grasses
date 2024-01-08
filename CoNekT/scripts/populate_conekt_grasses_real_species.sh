#!/usr/bin/env bash

BASE_DIR=/media/renato/SSD1TB/Repositories/conekt_grasses
SCRIPTS_DIR=$BASE_DIR/CoNekT/scripts
DATA_DIR=/media/renato/Renato_Backup/Projects/CENA/CoNekT_Bioenergy/v0.3
GENE_FAMILIES_DESCRIPTION="Gene Families Testing v0.3"

#Database credentials
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
 --interpro_xml $DATA_DIR/FunctionalData/interpro.xml\
 --gene_ontology_obo $DATA_DIR/FunctionalData/go.obo\
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with ontology data"
# TODO: add PECO data
$SCRIPTS_DIR/add/add_ontologies.py --plant_ontology $DATA_DIR/Ontology/plant-ontology.txt\
 --plant_e_c_ontology $DATA_DIR/Ontology/peco.tsv\
 --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with species data"
$SCRIPTS_DIR/add/add_species.py --input_table $DATA_DIR/info_species.tsv\
 --db_admin $DB_ADMIN \
 --db_name $DB_NAME \
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with gene descriptions"
for species_code in "Zma" "Osa" "Svi" "Bdi" "Pvi" "Sit" "Sbi"; do
 $SCRIPTS_DIR/add/add_gene_descriptions.py --species_code "$species_code"\
  --gene_descriptions $DATA_DIR/Species/"$species_code"/"$species_code"_cds_description.txt\
  --db_admin $DB_ADMIN\
  --db_name $DB_NAME\
  --db_password $DB_PASSWORD
done;

echo "Populating CoNekT Grasses with functional annotation data"
for species_code in "Zma" "Osa" "Svi" "Bdi" "Pvi" "Sit" "Sbi"; do
 $SCRIPTS_DIR/add/add_interproscan.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --interproscan_tsv $DATA_DIR/Species/"$species_code"/"$species_code"_interproscan.tsv\
 --species_code "$species_code"
done;

echo "Populating CoNekT Grasses with sugarcane functional annotation data"
for species_code in "Scp1" "Shc10" "Shc11" "Shc12" "Shc13" "Shc14" "Shc15" "Shc16" "Shc17" "Shc18" "Shc19" "Shc1" "Shc20" "Shc21" "Shc22" "Shc23" "Shc24" "Shc25" "Shc26" "Shc27" "Shc28" "Shc29" "Shc2" "Shc30" "Shc31" "Shc32" "Shc33" "Shc34" "Shc35" "Shc36" "Shc37" "Shc38" "Shc39" "Shc3" "Shc40" "Shc41" "Shc42" "Shc43" "Shc44" "Shc45" "Shc46" "Shc47" "Shc48" "Shc49" "Shc4" "Shc50" "Shc5" "Shc6" "Shc7" "Shc8" "Shc9"; do
 gzip -d $DATA_DIR/Species/Cana/InterProScan/"$species_code".aa.nonStop.interpro.tsv.gz
 $SCRIPTS_DIR/add/add_interproscan.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --interproscan_tsv $DATA_DIR/Species/Cana/InterProScan/"$species_code".aa.nonStop.interpro.tsv\
 --species_code "$species_code"
 gzip $DATA_DIR/Species/Cana/InterProScan/"$species_code".aa.nonStop.interpro.tsv
done;

echo "Populating CoNekT Grasses with expression profiles"
for species_code in "Zma" "Osa" "Svi" "Sbi"; do
 $SCRIPTS_DIR/add/add_expression_data.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "$species_code"\
 --expression_matrix $DATA_DIR/Species/"$species_code"/expression/"$species_code"_expression_matrix.txt\
 --sample_annotation $DATA_DIR/Species/"$species_code"/expression/"$species_code"_expression_annotation.txt
done;

echo "Populating CoNekT Grasses with sugarcane expression profiles"
species_code="Scp1"
$SCRIPTS_DIR/add/add_expression_data.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "$species_code"\
 --expression_matrix $DATA_DIR/Species/Cana/expression/"$species_code"_expression_matrix.txt\
 --sample_annotation $DATA_DIR/Species/Cana/expression/"$species_code"_expression_annotation.txt

echo "Populating CoNekT Grasses with expression specificities"
for species_code in "Zma" "Osa" "Svi" "Sbi" "Scp1"; do
 $SCRIPTS_DIR/build/calculate_specificities.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "$species_code"
done;

echo "Populating CoNekT Grasses with gene families"
$SCRIPTS_DIR/add/add_gene_families.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --orthogroups $DATA_DIR/OrthoFinder/Results_Nov25/Orthogroups/Orthogroups.txt\
 --description "$GENE_FAMILIES_DESCRIPTION"

echo "Update all counts in the database"
$SCRIPTS_DIR/build/update_counts.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD 
