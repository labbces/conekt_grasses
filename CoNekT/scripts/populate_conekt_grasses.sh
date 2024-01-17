#!/usr/bin/env bash

BASE_DIR=/home/conekt_admin/populate_conekt/conekt_grasses
SCRIPTS_DIR=$BASE_DIR/CoNekT/scripts
DATA_DIR=/DataBig/CoNeKt/Backups/01052024/v0.3
SPECIES_TABLE=$DATA_DIR/Species/species_info.tsv
SPECIES_ARRAY=( Svi Bdi Osa Sit Sbi Pvi Zma Scp1 Shc1 Shc2 Shc3 Shc4 Shc5 Shc6 Shc7 Shc8 Shc9 Shc10 Shc11 Shc12 Shc13 Shc14 Shc15 Shc16 Shc17 Shc18 Shc19 Shc20 Shc21 Shc22 Shc23 Shc24 Shc25 Shc26 Shc27 Shc28 Shc29 Shc30 Shc31 Shc32 Shc33 Shc34 Shc35 Shc36 Shc37 Shc38 Shc39 Shc40 Shc41 Shc42 Shc43 Shc44 Shc45 Shc46 Shc47 Shc48 Shc49 Shc50 )
SPECIES_EXPRESSION_PROFILES=(  )

# Description of method to generate gene families
GENE_FAMILIES_DESCRIPTION="OrthoFinder Gene Families v0.3"

#Database credentials for CoNekT Grasses from file
#Expected variables: DB_ADMIN, DB_NAME and DB_PASSWORD
MARIADB_CREDENTIALS_FILE=$SCRIPTS_DIR/mariadb_credentials.txt
source $MARIADB_CREDENTIALS_FILE

export FLASK_APP=run.py

cd $BASE_DIR/CoNekT
source bin/activate
flask initdb
if [ -d $BASE_DIR/CoNekT/migrations ]; then
  echo "Removing existing migrations folder, if exists"
  rm -fr $BASE_DIR/CoNekT/migrations
fi
flask db init

# Deactivate virtual environment
# Currently it is necessary because libraries in the virtual environment
# are not compatible with the libraries in the system used by the scripts
deactivate
source $SCRIPTS_DIR/Populate_CoNekT/bin/activate

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
$SCRIPTS_DIR/add/add_species.py --input_table $SPECIES_TABLE\
 --db_admin $DB_ADMIN \
 --db_name $DB_NAME \
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with gene descriptions"
for species_code in ${SPECIES_ARRAY[@]};
 do
 if [ -f $DATA_DIR/Species/"$species_code"/"$species_code"_cds_description.txt ]; then
  $SCRIPTS_DIR/add/add_gene_descriptions.py --species_code "$species_code"\
  --gene_descriptions $DATA_DIR/Species/"$species_code"/"$species_code"_cds_description.txt\
  --db_admin $DB_ADMIN\
  --db_name $DB_NAME\
  --db_password $DB_PASSWORD
 fi
done;

echo "Populating CoNekT Grasses with functional annotation data"species_code="Scp1"
for species_code in ${SPECIES_ARRAY[@]};
 do
  if [ -f $DATA_DIR/Species/"$species_code"/"$species_code".aa.nonStop.interpro.tsv.gz ]; then
   gzip -d $DATA_DIR/Species/"$species_code"/"$species_code".aa.nonStop.interpro.tsv.gz
   $SCRIPTS_DIR/add/add_interproscan.py --db_admin $DB_ADMIN\
    --db_name $DB_NAME\
    --db_password $DB_PASSWORD\
    --interproscan_tsv $DATA_DIR/Species/"$species_code"/"$species_code".aa.nonStop.interpro.tsv\
    --species_code "$species_code"
   gzip $DATA_DIR/Species/"$species_code"/"$species_code".aa.nonStop.interpro.tsv
  fi
done;

echo "Populating CoNekT Grasses with species GO annotation"
for species_code in ${SPECIES_ARRAY[@]};
 do
 if [ -f $DATA_DIR/Species/"$species_code"/"$species_code"_go.txt ]; then
 $SCRIPTS_DIR/add/add_go.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --go_tsv $DATA_DIR/Species/"$species_code"/"$species_code"_go.txt\
 --species_code "$species_code"\
 --annotation_source "GOs from InterProScan"
 fi
done;

echo "Populating CoNekT Grasses with expression profiles"
for species_code in ${SPECIES_ARRAY[@]};
 do
 if [ -f $DATA_DIR/Species/"$species_code"/expression/"$species_code"_expression_matrix.txt ]; then
 $SCRIPTS_DIR/add/add_expression_data.py --db_admin $DB_ADMIN\
  --db_name $DB_NAME\
  --db_password $DB_PASSWORD\
  --species_code "$species_code"\
  --expression_matrix $DATA_DIR/Species/"$species_code"/expression/"$species_code"_expression_matrix.txt\
  --sample_annotation $DATA_DIR/Species/"$species_code"/expression/"$species_code"_expression_annotation.txt
  SPECIES_EXPRESSION_PROFILES+=($species_code)
 fi
done;

echo "Populating CoNekT Grasses with expression specificity"
for species_code in ${SPECIES_EXPRESSION_PROFILES[@]};
 do
 $SCRIPTS_DIR/build/calculate_specificities.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "$species_code"
done;

echo "Populating CoNekT Grasses with expression networks"
$SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "Osa"\
 --network $DATA_DIR/Species/Osa/expression/Osa_PRJNA190188_network.txt\
 --description "Rice network (PRJNA190188, leaf sections)"

$SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "Zma"\
 --network $DATA_DIR/Species/Zma/expression/Zma_PRJNA190188_network.txt\
 --description "Maize network (PRJNA190188, leaf sections)"

$SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "Scp1"\
 --network $DATA_DIR/Species/Scp1/expression/PRJEB38368_network.txt\
 --description "Sugarcane network (Correr, 2020 - PRJEB38368)"

$SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "Scp1"\
 --network $DATA_DIR/Species/Scp1/expression/Hoang2017_network.txt\
 --description "Sugarcane network (Hoang, 2017)"

$SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "Scp1"\
 --network $DATA_DIR/Species/Scp1/expression/Perlo2022_network.txt\
 --description "Sugarcane network (Perlo, 2022)"

echo "Populating CoNekT Grasses with gene families"
$SCRIPTS_DIR/add/add_gene_families.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --orthogroups $DATA_DIR/OrthoFinder/Orthogroups.txt\
 --description "$GENE_FAMILIES_DESCRIPTION"

echo "Populating CoNekT Grasses with coexpression clusters"
$SCRIPTS_DIR/build/calculate_clusters.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --network_method_id 1\
 --description "Rice coexpression clusters (PRJNA190188, leaf sections)"

$SCRIPTS_DIR/build/calculate_clusters.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --network_method_id 2\
 --description "Maize coexpression clusters (PRJNA190188, leaf sections)"

$SCRIPTS_DIR/build/calculate_clusters.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --network_method_id 3\
 --description "Sugarcane coexpression clusters (Correr, 2020)"

$SCRIPTS_DIR/build/calculate_clusters.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --network_method_id 4\
 --description "Sugarcane coexpression clusters (Hoang, 2017)"

$SCRIPTS_DIR/build/calculate_clusters.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --network_method_id 5\
 --description "Sugarcane coexpression clusters (Perlo, 2022)"

echo "Update all counts in the database"
$SCRIPTS_DIR/build/update_counts.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD