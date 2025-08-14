#!/bin/bash

# This script clears all data from every table in your CoNekT database.
# All structures and constraints are kept.
#
# To run: bash /path/to/this/file/clear_database.sh


# Get variables from 'setup_variables.sh' file (copy/paste your full path to 'setup_variables.sh' file here)
source /home/pturquetti/conekt/conekt_grasses/CoNekT/scripts/setup_variables.sh

had_error=0  # Error counter

function run_mysql() {
    local query="$1"
    mysql -h "localhost" -u "$DB_ADMIN" -p"$DB_PASSWORD" "$DB_NAME" -e "$query"
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to execute query: $query"
        had_error=1
    fi
}

echo "⚠️  WARNING: This will delete ALL data from the database '$DB_NAME', but keep the structure and constraints."
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
  echo "❌ Operation cancelled."
  exit 0
fi

echo "Cleaning all tables in database '$DB_NAME':"

TABLES=$(mysql -h "localhost" -u "$DB_ADMIN" -p"$DB_PASSWORD" -Nse \
"SELECT table_name FROM information_schema.tables WHERE table_schema='$DB_NAME';")

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to fetch tables from database '$DB_NAME'."
    exit 1
fi

run_mysql "SET FOREIGN_KEY_CHECKS=0;"

for table in $TABLES; do
    echo "Cleaning table: $table"
    run_mysql "DELETE FROM \`$table\`;"
    run_mysql "ALTER TABLE \`$table\` AUTO_INCREMENT = 1;"
done

run_mysql "SET FOREIGN_KEY_CHECKS=1;"

if [ $had_error -eq 0 ]; then
    echo "✅ All tables in database '$DB_NAME' have been successfully cleaned."
else
    echo "⚠️ Finished cleaning with some errors. Please check the logs above."
fi
