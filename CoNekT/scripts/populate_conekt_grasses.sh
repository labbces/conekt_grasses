#!/usr/bin/env bash

# Get variables from 'setup_variables.sh' file (copy/paste your full path to file here)
source /home/pturquetti/conekt/conekt_grasses/CoNekT/scripts/setup_variables.sh

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
# deactivate
# source $SCRIPTS_DIR/Populate_CoNekT/bin/activate

# Activating virtual environment
deactivate
source $BASE_DIR/CoNekT/bin/activate
echo -e "Ready to start populating!"

echo -e "\nPopulating CoNekT Grasses with functional data"
$SCRIPTS_DIR/add/add_functional_data.py\
 --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --interpro_xml $DATA_DIR"/Functional Data/interpro.xml"\
 --gene_ontology_obo $DATA_DIR"/Functional Data/go.obo"\
 --cazyme $DATA_DIR"/Functional Data/CAZyDB.07302020.fam-activities.txt"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE
 

echo -e "\nPopulating CoNekT Grasses with ontology data"
$SCRIPTS_DIR/add/add_ontologies.py\
 --plant_ontology $DATA_DIR/Ontology/po.obo\
 --plant_e_c_ontology $DATA_DIR/Ontology/peco.obo\
 --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE

echo -e "\nPopulating CoNekT Grasses with species data"
$SCRIPTS_DIR/add/add_species.py\
 --input_table $SPECIES_TABLE\
 --db_admin $DB_ADMIN \
 --db_name $DB_NAME \
 --db_password $DB_PASSWORD\
 --species_dir $SPECIES_DIR\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE

echo -e "\nPopulating CoNekT Grasses with gene descriptions"
first_run=true
for species_code in ${SPECIES_ARRAY[@]};
 do
 if [ -f $SPECIES_DIR/"$species_code"/"$species_code"_cds_description.txt ]; then
  $SCRIPTS_DIR/add/add_gene_descriptions.py --species_code "$species_code"\
  --gene_descriptions $SPECIES_DIR/"$species_code"/"$species_code"_cds_description.txt\
  --db_admin $DB_ADMIN\
  --db_name $DB_NAME\
  --db_password $DB_PASSWORD\
  --logdir $LOG_DIR\
  --db_verbose $DB_VERBOSE\
  --py_verbose $PY_VERBOSE\
  --first_run $first_run
  first_run=false
 fi
done;





echo -e "\nPopulating CoNekT Grasses with functional annotation data"
first_run=true
for species_code in ${SPECIES_ARRAY[@]};
 do
  if [ -f $DATA_DIR/Species/"$species_code"/"$species_code"_interproscan.tsv ]; then
  #  gzip -d $DATA_DIR/Species/"$species_code"/"$species_code".aa.nonStop.interpro.tsv.gz
   $SCRIPTS_DIR/add/add_interproscan.py --db_admin $DB_ADMIN\
    --db_name $DB_NAME\
    --db_password $DB_PASSWORD\
    --interproscan_tsv $DATA_DIR/Species/"$species_code"/"$species_code"_interproscan.tsv\
    --species_code "$species_code"\
    --logdir $LOG_DIR\
    --db_verbose $DB_VERBOSE\
    --py_verbose $PY_VERBOSE\
    --first_run $first_run
    first_run=false
  #  gzip $DATA_DIR/Species/"$species_code"/"$species_code".aa.nonStop.interpro.tsv
  fi
done;



echo -e "\nPopulating CoNekT Grasses with species GO annotation"
first_run=true
for species_code in ${SPECIES_ARRAY[@]};
 do
 if [ -f $DATA_DIR/Species/"$species_code"/"$species_code"_go.txt ]; then
 $SCRIPTS_DIR/add/add_go.py --db_admin $DB_ADMIN\
    --db_name $DB_NAME\
    --db_password $DB_PASSWORD\
    --go_tsv $DATA_DIR/Species/"$species_code"/"$species_code"_go.txt\
    --species_code "$species_code"\
    --annotation_source "GOs from InterProScan"\
    --logdir $LOG_DIR\
    --db_verbose $DB_VERBOSE\
    --py_verbose $PY_VERBOSE\
    --first_run $first_run
 first_run=false
 fi
done;





echo "Populating CoNekT Grasses with species CAZyme annotation"
first_run=true
for species_code in ${SPECIES_ARRAY[@]};
 do
 if [ -f $DATA_DIR/Species/"$species_code"/"$species_code"_cazymes.txt ]; then
 $SCRIPTS_DIR/add/add_cazymes.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --cazyme_tsv $DATA_DIR/Species/"$species_code"/"$species_code"_cazymes.txt\
 --species_code "$species_code"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE\
 --first_run $first_run
 first_run=false
 fi
done;


# From this point on, insertion scripts use the populate virtual environment. 
# Custom logs not yet implemented.
deactivate
source $SCRIPTS_DIR/Populate_CoNekT/bin/activate

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