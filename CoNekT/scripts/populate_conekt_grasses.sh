#!/usr/bin/env bash

# Parar imediatamente se qualquer comando falhar (exceto durante verificações)
set -e

# --- Configuração de caminhos (AJUSTE ESTES PARA SEU AMBIENTE) ---
BASE_DIR=${HOME}/repositorios/conekt_grasses
SCRIPTS_DIR=$BASE_DIR/CoNekT/scripts
DATA_DIR=${HOME}/repositorios/conekt_dados/v0.3

SPECIES_TABLE=$DATA_DIR/Species/info_species.tsv
SPECIES_ARRAY=( Scp1 )
SPECIES_EXPRESSION_PROFILES=()

GENE_FAMILIES_DESCRIPTION="OrthoFinder Gene Families v0.3"

# --- Credenciais do banco ---
MARIADB_CREDENTIALS_FILE=$SCRIPTS_DIR/mariadb_credentials.txt
if [ ! -f "$MARIADB_CREDENTIALS_FILE" ]; then
  echo "ERRO: Arquivo de credenciais não encontrado: $MARIADB_CREDENTIALS_FILE"
  exit 1
fi

# Carrega credenciais com segurança (protege caracteres especiais)
set -a
source <(grep -v '^#' "$MARIADB_CREDENTIALS_FILE" | sed 's/=\(.*\)/="\1"/')
set +a

export FLASK_APP=run.py

# --- Função auxiliar para exibir etapas ---
log_step() {
  echo "========================================"
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
  echo "========================================"
}

# --- Função: verificar se dados foram carregados ---
verify_data_loaded() {
  local table="$1"
  local expected_min="$2"
  local description="$3"
  
  # Cria arquivo de configuração temporário
  local my_cnf="/tmp/mysql_verify.cnf"
  cat > "$my_cnf" << EOF
[client]
user=$DB_ADMIN
password=$DB_PASSWORD
host=localhost
database=$DB_NAME
EOF
  chmod 600 "$my_cnf"
  
  set +e
  count=$(mysql --defaults-file="$my_cnf" -se "SELECT COUNT(*) FROM $table;" 2>/dev/null)
  exit_code=$?
  set -e
  
  # Limpa arquivo temporário
  rm -f "$my_cnf"
  
  if [ $exit_code -ne 0 ] || [ -z "$count" ]; then
    echo "❌ ALERTA: Não foi possível verificar $description (erro na consulta)"
    return 1
  fi
  
  if [ "$count" -lt "$expected_min" ]; then
    echo "❌ ALERTA: $description tem apenas $count registros (esperado ≥ $expected_min)"
    return 1
  else
    echo "✅ $description: $count registros"
    return 0
  fi
}

# --- Etapa 1: Inicialização do banco de dados ---
log_step "Inicializando o banco de dados CoNekT Grasses"
cd "$BASE_DIR/CoNekT"
source bin/activate
flask initdb

if [ -d "$BASE_DIR/CoNekT/migrations" ]; then
  echo "Removendo pasta de migrações existente..."
  rm -rf "$BASE_DIR/CoNekT/migrations"
fi
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
deactivate

# --- Etapa 2: Ativar ambiente de população ---
log_step "Ativando ambiente virtual para população de dados"
source "$SCRIPTS_DIR/Populate_CoNekT/bin/activate"

# --- Etapa 3: Dados funcionais ---
log_step "Populando dados funcionais (InterPro, GO, CAZy)"
"$SCRIPTS_DIR/add/add_functional_data.py" \
  --db_admin "$DB_ADMIN" \
  --db_name "$DB_NAME" \
  --interpro_xml "$DATA_DIR/FunctionalData/interpro.xml" \
  --gene_ontology_obo "$DATA_DIR/FunctionalData/go.obo" \
  --cazyme "$DATA_DIR/FunctionalData/CAZyDB.08062022.fam-activities.txt" \
  --db_password "$DB_PASSWORD"

# Verificação após dados funcionais
verify_data_loaded "go" 1000 "Termos GO"
verify_data_loaded "cazyme" 100 "Famílias CAZy"
verify_data_loaded "interpro" 1000 "Domínios InterPro"

# --- Etapa 4: Ontologias ---
log_step "Populando ontologias"
"$SCRIPTS_DIR/add/add_ontologies.py" \
  --plant_ontology "$DATA_DIR/Ontology/plant-ontology.txt" \
  --plant_e_c_ontology "$DATA_DIR/Ontology/peco.tsv" \
  --db_admin "$DB_ADMIN" \
  --db_name "$DB_NAME" \
  --db_password "$DB_PASSWORD"

# Verificação após ontologias
verify_data_loaded "plant_ontology" 1000 "Termos Plant Ontology"
verify_data_loaded "plant_experimental_conditions_ontology" 100 "Termos PECO"

# --- Etapa 5: Espécies ---
log_step "Populando dados de espécies"
"$SCRIPTS_DIR/add/add_species.py" \
  --input_table "$SPECIES_TABLE" \
  --db_admin "$DB_ADMIN" \
  --db_name "$DB_NAME" \
  --db_password "$DB_PASSWORD"

# Verificação após espécies
verify_data_loaded "species" 1 "Espécies"
verify_data_loaded "sequences" 10000 "Genes"

# --- Etapa 6: Descrições gênicas ---
log_step "Populando descrições gênicas por espécie"
for species_code in "${SPECIES_ARRAY[@]}"; do
  desc_file="$DATA_DIR/Species/$species_code/${species_code}_cds_description.txt"
  if [ -f "$desc_file" ]; then
    "$SCRIPTS_DIR/add/add_gene_descriptions.py" \
      --species_code "$species_code" \
      --gene_descriptions "$desc_file" \
      --db_admin "$DB_ADMIN" \
      --db_name "$DB_NAME" \
      --db_password "$DB_PASSWORD"
  else
    echo "Aviso: arquivo de descrição não encontrado para $species_code"
  fi
done

# --- Etapa 7: Anotações InterProScan ---
log_step "Populando anotações InterProScan"
for species_code in "${SPECIES_ARRAY[@]}"; do
  interpro_file=""

  # Tenta os mesmos nomes usados no script de validação
  for candidate in \
    "${species_code}.aa.nonStop.interpro.tsv.gz" \
    "${species_code}_interproscan.tsv.gz" \
    "${species_code}.aa.nonStop.interpro.tsv" \
    "${species_code}_interproscan.tsv"; do
    
    if [ -f "$DATA_DIR/Species/$species_code/$candidate" ]; then
      interpro_file="$DATA_DIR/Species/$species_code/$candidate"
      break
    fi
  done

  if [ -z "$interpro_file" ]; then
    echo "Aviso: arquivo InterProScan não encontrado para $species_code (mas validação prévia deveria ter impedido isso)"
    continue
  fi

  # Preparar caminho para o TSV descompactado
  if [[ "$interpro_file" == *.gz ]]; then
    # Descompacta para /tmp sem alterar original
    tsv_to_use="/tmp/${species_code}_interproscan.tsv"
    gunzip -c "$interpro_file" > "$tsv_to_use"
  else
    # Usa diretamente
    tsv_to_use="$interpro_file"
  fi

  # Executa o script Python
  "$SCRIPTS_DIR/add/add_interproscan.py" \
    --db_admin "$DB_ADMIN" \
    --db_name "$DB_NAME" \
    --db_password "$DB_PASSWORD" \
    --interproscan_tsv "$tsv_to_use" \
    --species_code "$species_code"

  # Limpa arquivo temporário, se criado
  if [[ "$interpro_file" == *.gz ]]; then
    rm -f "$tsv_to_use"
  fi
done

# Verificação após InterProScan
verify_data_loaded "sequence_interpro" 1000 "Anotações InterProScan"

# --- Etapa 8: Anotações GO ---
log_step "Populando anotações GO por espécie"
for species_code in "${SPECIES_ARRAY[@]}"; do
  go_file="$DATA_DIR/Species/$species_code/${species_code}_go.txt"
  if [ -f "$go_file" ]; then
    "$SCRIPTS_DIR/add/add_go.py" \
      --db_admin "$DB_ADMIN" \
      --db_name "$DB_NAME" \
      --db_password "$DB_PASSWORD" \
      --go_tsv "$go_file" \
      --species_code "$species_code" \
      --annotation_source "GOs from InterProScan"
  fi
done

# Verificação após GO
verify_data_loaded "sequence_go" 10000 "Anotações GO"

# --- Etapa 9: CAZymes ---
log_step "Populando anotações CAZyme por espécie"
for species_code in "${SPECIES_ARRAY[@]}"; do
  cazyme_file="$DATA_DIR/Species/$species_code/${species_code}_cazymes.txt"
  if [ -f "$cazyme_file" ]; then
    "$SCRIPTS_DIR/add/add_cazymes.py" \
      --db_admin "$DB_ADMIN" \
      --db_name "$DB_NAME" \
      --db_password "$DB_PASSWORD" \
      --cazyme_tsv "$cazyme_file" \
      --species_code "$species_code"
  fi
done

# Verificação após CAZymes
verify_data_loaded "sequence_cazyme" 100 "Anotações CAZyme"

# --- Etapa 10: Perfis de expressão ---
log_step "Populando perfis de expressão"
for species_code in "${SPECIES_ARRAY[@]}"; do
  expr_matrix="$DATA_DIR/Species/$species_code/${species_code}_expression_matrix.txt"
  if [ -f "$expr_matrix" ]; then
    "$SCRIPTS_DIR/add/add_expression_data.py" \
      --db_admin "$DB_ADMIN" \
      --db_name "$DB_NAME" \
      --db_password "$DB_PASSWORD" \
      --species_code "$species_code" \
      --expression_matrix "$expr_matrix" \
      --sample_annotation "$DATA_DIR/Species/$species_code/${species_code}_expression_annotation.txt"
    SPECIES_EXPRESSION_PROFILES+=("$species_code")
  fi
done

# Verificação após expressão
verify_data_loaded "samples" 1 "Amostras"
verify_data_loaded "expression_profiles" 1000 "Perfis de expressão"

# --- Etapa 11: Especificidade de expressão ---
if [ ${#SPECIES_EXPRESSION_PROFILES[@]} -gt 0 ]; then
  log_step "Calculando especificidade de expressão"
  for species_code in "${SPECIES_EXPRESSION_PROFILES[@]}"; do
    "$SCRIPTS_DIR/build/calculate_specificities.py" \
      --db_admin "$DB_ADMIN" \
      --db_name "$DB_NAME" \
      --db_password "$DB_PASSWORD" \
      --species_code "$species_code"
  done
  verify_data_loaded "expression_specificity" 1000 "Especificidade de expressão"
else
  echo "Nenhum perfil de expressão encontrado. Pulando cálculo de especificidade."
fi

# --- Etapa 12: Redes de coexpressão ---
log_step "Populando redes de coexpressão"
# Osa
#  "$SCRIPTS_DIR/add/add_network.py" \
#    --db_admin "$DB_ADMIN" --db_name "$DB_NAME" --db_password "$DB_PASSWORD" \
#    --species_code "Osa" \
#    --network "$DATA_DIR/Species/Osa/Osa_PRJNA190188_network.txt" \
#    --description "Rice network (PRJNA190188, leaf sections)"

# Verificação após redes

#verify_data_loaded "expression_networks" 1000 "Redes de coexpressão"

# Zma
#  "$SCRIPTS_DIR/add/add_network.py" \
#    --db_admin "$DB_ADMIN" --db_name "$DB_NAME" --db_password "$DB_PASSWORD" \
#    --species_code "Zma" \
#    --network "$DATA_DIR/Species/Zma/Zma_PRJNA551002_network.txt" \
#    --description "Maize network (PRJNA551002, leaf sections)"

# Scp1 - múltiplas redes
#for net in "Correr2020" "Hoang2017" "Perlo2022"; do
#  "$SCRIPTS_DIR/add/add_network.py" \
#    --db_admin "$DB_ADMIN" --db_name "$DB_NAME" --db_password "$DB_PASSWORD" \
#    --species_code "Scp1" \
#    --network "$DATA_DIR/Species/Scp1_v1/${net}_network.txt" \
#    --description "Sugarcane network ($net)"
#done

# --- Etapa 13: Famílias gênicas ---
log_step "Populando famílias gênicas"
"$SCRIPTS_DIR/add/add_gene_families.py" \
  --db_admin "$DB_ADMIN" \
  --db_name "$DB_NAME" \
  --db_password "$DB_PASSWORD" \
  --orthogroups "$DATA_DIR/ComparativeGenomics/Orthogroups.txt" \
  --description "$GENE_FAMILIES_DESCRIPTION"

# Verificação após famílias gênicas
verify_data_loaded "gene_families" 10000 "Famílias gênicas"
verify_data_loaded "sequence_family" 10000 "Associações família-gene"

# --- Etapa 14: Clusters de coexpressão ---
log_step "Calculando clusters de coexpressão"
for id_desc in \
#  "1|Rice coexpression clusters (PRJNA190188, leaf sections)" \
#  "2|Maize coexpression clusters (PRJNA551002, leaf sections)" \
#  "3|Sugarcane coexpression clusters (Correr, 2020)" \
#  "4|Sugarcane coexpression clusters (Hoang, 2017)" \
#  "5|Sugarcane coexpression clusters (Perlo, 2022)"
do

  method_id="${id_desc%%|*}"
  desc="${id_desc#*|}"
  "$SCRIPTS_DIR/build/calculate_clusters.py" \
    --db_admin "$DB_ADMIN" \
    --db_name "$DB_NAME" \
    --db_password "$DB_PASSWORD" \
    --network_method_id "$method_id" \
    --description "$desc"
done

# Verificação após clusters
verify_data_loaded "coexpression_clusters" 100 "Clusters de coexpressão"

# --- Etapa final: Atualizar contagens ---
log_step "Atualizando contagens no banco de dados"
"$SCRIPTS_DIR/build/update_counts.py" \
  --db_admin "$DB_ADMIN" \
  --db_name "$DB_NAME" \
  --db_password "$DB_PASSWORD"

# Verificação final
verify_data_loaded "species" 1 "Espécies (verificação final)"

log_step "Pipeline concluído com sucesso!"
