#!/usr/bin/env bash

# Get variables from 'setup_variables.sh' file (copy/paste your full path to file here)
source /home/pturquetti/conekt/conekt_grasses/CoNekT/scripts/setup_variables.sh

timestamp_init=$(date +"%Y-%m-%d %H:%M:%S")

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
 --cazyme $DATA_DIR"/Functional Data/CAZyDB.08062022.fam-activities.txt"\
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

echo "Populating CoNekT Grasses with TE Classes"
$SCRIPTS_DIR/add/add_te_classes.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --te_classes $DATA_DIR"/Transposable Elements/TE_Classes.tsv"\
 --description "$TE_CLASSES_DESCRIPTION"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE

echo -e "\nPopulating CoNekT Grasses with species data"
$SCRIPTS_DIR/add/add_species.py --db_admin $DB_ADMIN \
 --db_name $DB_NAME \
 --db_password $DB_PASSWORD\
 --input_table $SPECIES_TABLE\
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





echo -e "\nPopulating CoNekT Grasses with species CAZyme annotation"
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




echo -e "\nPopulating CoNekT Grasses with expression profiles"
first_run=true
for species_code in ${SPECIES_ARRAY[@]};
 do
 if [ -f $DATA_DIR/Species/"$species_code"/"$species_code"_expression_matrix.txt ]; then
 $SCRIPTS_DIR/add/add_expression_data.py --db_admin $DB_ADMIN\
  --db_name $DB_NAME\
  --db_password $DB_PASSWORD\
  --species_code "$species_code"\
  --expression_matrix $DATA_DIR/Species/"$species_code"/"$species_code"_expression_matrix.txt\
  --sample_annotation $DATA_DIR/Species/"$species_code"/"$species_code"_expression_annotation.txt\
  --logdir $LOG_DIR\
  --db_verbose $DB_VERBOSE\
  --py_verbose $PY_VERBOSE\
  --first_run $first_run
  first_run=false
  SPECIES_EXPRESSION_PROFILES+=($species_code)
 fi
done;



echo -e "\nPopulating CoNekT Grasses with expression specificity"
first_run=true
for species_code in ${SPECIES_EXPRESSION_PROFILES[@]};
 do
 $SCRIPTS_DIR/build/calculate_specificities.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "$species_code"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE\
 --first_run $first_run
 first_run=false
done;




echo "Populating CoNekT Grasses with expression networks"
first_run=true
$SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "Osa"\
 --network $DATA_DIR/Species/Osa/Rice_PRJNA190188_network.txt\
 --description "Rice network (PRJNA190188, leaf sections)"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE\
 --first_run $first_run
 first_run=false


$SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --species_code "Zma"\
 --network $DATA_DIR/Species/Zma/Maize_PRJNA551002_network.txt\
 --description "Maize network (PRJNA190188, leaf sections)"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE\
 --first_run $first_run

# $SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
#  --db_name $DB_NAME\
#  --db_password $DB_PASSWORD\
#  --species_code "Scp1"\
#  --network $DATA_DIR/Species/Scp1/expression/PRJEB38368_network.txt\
#  --description "Sugarcane network (Correr, 2020 - PRJEB38368)"

# $SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
#  --db_name $DB_NAME\
#  --db_password $DB_PASSWORD\
#  --species_code "Scp1"\
#  --network $DATA_DIR/Species/Scp1/expression/Hoang2017_network.txt\
#  --description "Sugarcane network (Hoang, 2017)"

# $SCRIPTS_DIR/add/add_network.py --db_admin $DB_ADMIN\
#  --db_name $DB_NAME\
#  --db_password $DB_PASSWORD\
#  --species_code "Scp1"\
#  --network $DATA_DIR/Species/Scp1/expression/Perlo2022_network.txt\
#  --description "Sugarcane network (Perlo, 2022)"

# From this point on, insertion scripts use the populate virtual environment. 
# Custom logs not yet implemented.

echo "Populating CoNekT Grasses with gene families"
$SCRIPTS_DIR/add/add_gene_families.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --orthogroups "$DATA_DIR/Comparative Genomics/Orthogroups.txt"\
 --description "$GENE_FAMILIES_DESCRIPTION"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE

echo "Populating CoNekT Grasses with TEdistill sequences"
$SCRIPTS_DIR/add/add_tedistills.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --sequences $DATA_DIR"/Transposable Elements/TEdistill_sequences.fa"\
 --orthogroups $DATA_DIR"/Transposable Elements/Orthogroups_TEdistill.txt"\
 --description "$TEDISTILL_DESCRIPTION"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE

echo "Populating CoNekT Grasses with coexpression clusters"
$SCRIPTS_DIR/build/calculate_clusters.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --network_method_id 1\
 --description "Rice coexpression clusters (PRJNA190188, leaf sections)"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE

$SCRIPTS_DIR/build/calculate_clusters.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --network_method_id 2\
 --description "Maize coexpression clusters (PRJNA190188, leaf sections)"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE

#$SCRIPTS_DIR/build/calculate_clusters.py --db_admin $DB_ADMIN\
# --db_name $DB_NAME\
# --db_password $DB_PASSWORD\
# --network_method_id 3\
# --description "Sugarcane coexpression clusters (Correr, 2020)"

#$SCRIPTS_DIR/build/calculate_clusters.py --db_admin $DB_ADMIN\
# --db_name $DB_NAME\
# --db_password $DB_PASSWORD\
# --network_method_id 4\
# --description "Sugarcane coexpression clusters (Hoang, 2017)"

#$SCRIPTS_DIR/build/calculate_clusters.py --db_admin $DB_ADMIN\
# --db_name $DB_NAME\
# --db_password $DB_PASSWORD\
# --network_method_id 5\
# --description "Sugarcane coexpression clusters (Perlo, 2022)"

echo "Populating CoNekT Grasses with species TR families annotation"
 $SCRIPTS_DIR/add/add_trs.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --tr_families $DATA_DIR/"Functional Data/TRs/RulesFull_Jennifer_JEIN_05122024.txt"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE

echo "Populating CoNekT Grasses with species TR annotation"
first_run=true
for species_code in ${SPECIES_ARRAY[@]};
 do
 if [ -f $DATA_DIR/Species/"$species_code"/*_list_TFs_OTRs_Orphans.txt ]; then
 $SCRIPTS_DIR/add/add_trs.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --tr_associations $DATA_DIR/Species/"$species_code"/*_list_TFs_OTRs_Orphans.txt\
 --species_code "$species_code"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE\
 --first_run $first_run
 first_run=false
 fi
done;

echo "Update all counts in the database"
$SCRIPTS_DIR/build/update_counts.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE

timestamp_end=$(date +"%Y-%m-%d %H:%M:%S")

echo "Script started at: $timestamp_init"
echo "Script ended at: $timestamp_end"
echo "Time taken: $(date -u -d @$(( $(date -d "$timestamp_end" +%s) - $(date -d "$timestamp_init" +%s) )) +%H:%M:%S)"
echo "CoNekT Grasses database populated successfully!"