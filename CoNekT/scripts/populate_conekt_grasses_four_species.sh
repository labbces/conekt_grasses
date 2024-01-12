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

species_table="info_four_species.tsv"

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
$SCRIPTS_DIR/add/add_species.py --input_table $DATA_DIR/"$species_table"\
 --db_admin $DB_ADMIN \
 --db_name $DB_NAME \
 --db_password $DB_PASSWORD

echo "Populating CoNekT Grasses with gene descriptions"
for species_code in Svi Osa Zma;
 do
 $SCRIPTS_DIR/add/add_gene_descriptions.py --species_code "$species_code"\
 --gene_descriptions $DATA_DIR/Species/"$species_code"/"$species_code"_cds_description.txt\
 --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD
done;

echo "Populating CoNekT Grasses with functional annotation data"
for species_code in Svi Osa Zma;
 do
 $SCRIPTS_DIR/add/add_interproscan.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --interproscan_tsv $DATA_DIR/Species/"$species_code"/"$species_code"_interproscan.tsv\
 --species_code "$species_code"
done;

echo "Populating CoNekT Grasses with sugarcane functional annotation data"
species_code="Scp1"
gzip -d $DATA_DIR/Species/Cana/InterProScan/"$species_code".aa.nonStop.interpro.tsv.gz
$SCRIPTS_DIR/add/add_interproscan.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --interproscan_tsv $DATA_DIR/Species/Cana/InterProScan/"$species_code".aa.nonStop.interpro.tsv\
 --species_code "$species_code"
gzip $DATA_DIR/Species/Cana/InterProScan/"$species_code".aa.nonStop.interpro.tsv

echo "Populating CoNekT Grasses with species GO annotation"
for species_code in Svi Osa Zma;
 do
 $SCRIPTS_DIR/add/add_go.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --go_tsv $DATA_DIR/Species/"$species_code"/"$species_code"_go.txt\
 --species_code "$species_code"\
 --annotation_source "GOs from InterProScan"
done;

echo "Populating CoNekT Grasses with sugarcane GO annotation"
species_code="Scp1"
$SCRIPTS_DIR/add/add_go.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --go_tsv $DATA_DIR/Species/Cana/Sequences/Scp_v1/"$species_code"_go.txt\
 --species_code "$species_code"\
 --annotation_source "GOs from InterProScan"

echo "Populating CoNekT Grasses with expression profiles"
for species_code in Svi Osa Zma;
 do
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

echo "Populating CoNekT Grasses with expression specificity"
for species_code in Svi Osa Zma;
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
 --network $DATA_DIR/Species/Cana/Correr2020/PRJEB38368_network.txt\
 --description "Sugarcane network (Correr, 2020 - PRJEB38368)"

$SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "Scp1"\
 --network $DATA_DIR/Species/Cana/Hoang2017/Hoang2017_network.txt\
 --description "Sugarcane network (Hoang, 2017)"

$SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "Scp1"\
 --network $DATA_DIR/Species/Cana/Perlo2022/Perlo2022_network.txt\
 --description "Sugarcane network (Perlo, 2022)"

echo "Populating CoNekT Grasses with gene families"
$SCRIPTS_DIR/add/add_gene_families.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --orthogroups $DATA_DIR/OrthoFinder/Results_Nov25/Orthogroups/Orthogroups.txt\
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