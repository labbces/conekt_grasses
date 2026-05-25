#!/usr/bin/env bash
#
# Isolated test runner for add_tedistills.py.
# Assumes the rest of the populate (species, sequences, te_classes) has already
# been loaded successfully. Before running, clear the TEdistill tables with
# cleanup_tedistills.sql.
#
# Usage:
#   1. mysql -u $DB_ADMIN -p $DB_NAME < cleanup_tedistills.sql
#   2. bash test_tedistills.sh

set -e  # abort on first error

# Reuse the same variables as the main populate
source /home/jnov/ConnektGrasses/conekt_grasses/CoNekT/scripts/setup_variables.sh

timestamp_init=$(date +"%Y-%m-%d %H:%M:%S")

export FLASK_APP=run.py
cd $BASE_DIR/CoNekT

# Activate the same virtualenv the populate uses
source bin/activate

echo "==========================================================="
echo "Testing add_tedistills.py only"
echo "Started at: $timestamp_init"
echo "==========================================================="

$SCRIPTS_DIR/add/add_tedistills.py --db_admin $DB_ADMIN\
 --db_name $DB_NAME\
 --db_password $DB_PASSWORD\
 --sequences "$DATA_DIR/Transposable Elements/distilledTE.flTE.iter56.fa"\
 --species_dir $SPECIES_DIR\
 --description "$TEDISTILL_DESCRIPTION"\
 --logdir $LOG_DIR\
 --db_verbose $DB_VERBOSE\
 --py_verbose $PY_VERBOSE

timestamp_end=$(date +"%Y-%m-%d %H:%M:%S")
echo "==========================================================="
echo "Started:  $timestamp_init"
echo "Finished: $timestamp_end"
echo "==========================================================="