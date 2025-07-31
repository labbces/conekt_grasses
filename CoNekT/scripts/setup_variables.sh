# ==================== Database Credentials ====================
# Set your database credentials below
DB_ADMIN=
DB_NAME=
DB_PASSWORD=''          # Use quotes for special characters



# ==================== Directory Paths ====================
# Base path of your CoNekT project (e.g, /home/user/conekt/conekt_grasses/). Set value here
BASE_DIR=/home/pturquetti/conekt/conekt_grasses/

# Path where your input data files are stored
DATA_DIR=/mnt/c/Users/Usuario/Desktop/DadosConekt

# Path to the CoNekT scripts and for saving log files during the populate process (auto-filled based on BASE_DIR)
SCRIPTS_DIR=$BASE_DIR/CoNekT/scripts                    
LOG_DIR=$BASE_DIR/CoNekT/scripts/add/logs_populate      



# ==================== Species Information ====================
# Path to the TSV file containing species metadata
SPECIES_TABLE=$DATA_DIR/Species/species_info.tsv

# Array of species codes to include (must match codes in SPECIES_TABLE exactly)
SPECIES_ARRAY=( Svi Osa Sit Sbi )

#
SPECIES_EXPRESSION_PROFILES=(  )

# Description of method to generate gene families
GENE_FAMILIES_DESCRIPTION="OrthoFinder Gene Families v0.3"



# ==================== Verbosity Settings ====================
# Whether to show detailed output from the database operations (recommended: false)
DB_VERBOSE=false

# Whether to show detailed output from populate Python scripts (recommended: true)
PY_VERBOSE=true