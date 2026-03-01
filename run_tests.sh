#!/bin/bash
# Script para executar testes automatizados com pytest

set -e  # Sair em caso de erro

source CoNekT/bin/activate

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sem cor

# Diretório base do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Criar diretório de resultados de testes
TEST_RESULTS_DIR="$PROJECT_DIR/CoNekT/tests/results"

# Timestamp para os arquivos de resultados
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Função para imprimir mensagens coloridas
print_message() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Função para mostrar ajuda
show_help() {
    cat << EOF
Uso: $0 [opções]

Opções:
    -h, --help              Mostra esta mensagem de ajuda
    -u, --unit              Executa apenas testes unitários
    -i, --integration       Executa apenas testes de integração
    -s, --slow              Executa também testes lentos
    -m, --markers MARKERS   Executa testes com marcadores específicos (ex: "unit and website")
    -k, --keyword KEYWORD   Executa testes que correspondem à palavra-chave
    -v, --verbose           Modo verboso (mais detalhes)
    -q, --quiet             Modo silencioso (menos detalhes)
    -x, --exitfirst         Para na primeira falha
    -f, --failed            Executa apenas testes que falharam na última execução
    --lf, --last-failed     Igual a --failed
    --ff, --failed-first    Executa testes que falharam primeiro, depois os outros
    --nf, --new-first       Executa testes novos primeiro
    -n, --numprocesses N    Executa testes em paralelo com N processos
    --cov                   Gera relatório de cobertura
    --no-cov                Não gera relatório de cobertura
    --html                  Gera relatório HTML
    --xml                   Gera relatório XML
    --pdb                   Ativa debugger Python em falhas
    --setup-show            Mostra setup e teardown de fixtures
    --markers               Lista todos os marcadores disponíveis
    --collect-only          Lista testes sem executá-los

Exemplos:
    $0                      # Executa todos os testes
    $0 -u                   # Executa apenas testes unitários
    $0 -m "unit and website"  # Executa testes unitários do website
    $0 -k "test_login"      # Executa testes que contém "test_login" no nome
    $0 -x -v                # Para na primeira falha, modo verboso
    $0 -n 4                 # Executa testes em paralelo com 4 processos
    $0 --failed             # Executa apenas testes que falharam

EOF
}

# Argumentos padrão
PYTEST_ARGS=""

# Processa argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--unit)
            PYTEST_ARGS="$PYTEST_ARGS -m unit"
            shift
            ;;
        -i|--integration)
            PYTEST_ARGS="$PYTEST_ARGS -m integration"
            shift
            ;;
        -s|--slow)
            PYTEST_ARGS="$PYTEST_ARGS -m slow"
            shift
            ;;
        -m|--markers)
            PYTEST_ARGS="$PYTEST_ARGS -m \"$2\""
            shift 2
            ;;
        -k|--keyword)
            PYTEST_ARGS="$PYTEST_ARGS -k \"$2\""
            shift 2
            ;;
        -v|--verbose)
            PYTEST_ARGS="$PYTEST_ARGS -vv"
            shift
            ;;
        -q|--quiet)
            PYTEST_ARGS="$PYTEST_ARGS -q"
            shift
            ;;
        -x|--exitfirst)
            PYTEST_ARGS="$PYTEST_ARGS -x"
            shift
            ;;
        -f|--failed|--lf|--last-failed)
            PYTEST_ARGS="$PYTEST_ARGS --lf"
            shift
            ;;
        --ff|--failed-first)
            PYTEST_ARGS="$PYTEST_ARGS --ff"
            shift
            ;;
        --nf|--new-first)
            PYTEST_ARGS="$PYTEST_ARGS --nf"
            shift
            ;;
        -n|--numprocesses)
            PYTEST_ARGS="$PYTEST_ARGS -n $2"
            shift 2
            ;;
        --cov)
            PYTEST_ARGS="$PYTEST_ARGS --cov=CoNekT/conekt --cov-report=term-missing --cov-report=html:$TEST_RESULTS_DIR/htmlcov_$TIMESTAMP"
            shift
            ;;
        --no-cov)
            PYTEST_ARGS="$PYTEST_ARGS --no-cov"
            shift
            ;;
        --html)
            PYTEST_ARGS="$PYTEST_ARGS --html=$TEST_RESULTS_DIR/pytest-report_$TIMESTAMP.html --self-contained-html"
            shift
            ;;
        --xml)
            PYTEST_ARGS="$PYTEST_ARGS --junitxml=$TEST_RESULTS_DIR/pytest-report_$TIMESTAMP.xml"
            shift
            ;;
        --pdb)
            PYTEST_ARGS="$PYTEST_ARGS --pdb"
            shift
            ;;
        --setup-show)
            PYTEST_ARGS="$PYTEST_ARGS --setup-show"
            shift
            ;;
        --markers)
            print_message "$YELLOW" "Marcadores disponíveis:"
            cd CoNekT && python -m pytest --markers
            exit 0
            ;;
        --collect-only)
            PYTEST_ARGS="$PYTEST_ARGS --collect-only"
            shift
            ;;
        *)
            print_message "$RED" "Opção desconhecida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Verifica se pytest está instalado
if ! command -v pytest &> /dev/null; then
    print_message "$RED" "❌ Erro: pytest não está instalado!"
    print_message "$YELLOW" "Execute: pip install -r requirements.txt"
    exit 1
fi

# Verifica se está no ambiente virtual
if [[ -z "$VIRTUAL_ENV" ]]; then
    print_message "$YELLOW" "⚠️  Aviso: Ambiente virtual não detectado!"
    print_message "$YELLOW" "Recomenda-se ativar o ambiente virtual antes de executar os testes."
    read -p "Continuar mesmo assim? (s/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi

# Imprime informações
print_message "$GREEN" "🧪 Executando testes CoNekT..."
print_message "$YELLOW" "Diretório: $PROJECT_DIR"
print_message "$YELLOW" "Argumentos: $PYTEST_ARGS"
echo

# Exporta variáveis de ambiente necessárias
export PYTHONPATH="${PROJECT_DIR}:${PYTHONPATH}"

# Executa pytest com logs
cd CoNekT
echo "Logs de execução serão salvos em: $TEST_RESULTS_DIR/pytest-log_$TIMESTAMP.txt"
eval "python -m pytest $PYTEST_ARGS" 2>&1 | tee "$TEST_RESULTS_DIR/pytest-log_$TIMESTAMP.txt"
EXIT_CODE=${PIPESTATUS[0]}

# Mensagem de resultado
echo
if [ $EXIT_CODE -eq 0 ]; then
    print_message "$GREEN" "✅ Todos os testes passaram com sucesso!"
else
    print_message "$RED" "❌ Alguns testes falharam!"
fi

# Informações sobre resultados salvos
print_message "$YELLOW" "📁 Resultados salvos em: $TEST_RESULTS_DIR"
print_message "$YELLOW" "📋 Log de execução: pytest-log_$TIMESTAMP.txt"

# Verifica se há relatório de cobertura
if [ -d "$TEST_RESULTS_DIR/htmlcov_$TIMESTAMP" ]; then
    print_message "$YELLOW" "📊 Relatório de cobertura HTML: htmlcov_$TIMESTAMP/index.html"
fi

# Verifica se há relatório HTML
if [ -f "$TEST_RESULTS_DIR/pytest-report_$TIMESTAMP.html" ]; then
    print_message "$YELLOW" "📄 Relatório HTML: pytest-report_$TIMESTAMP.html"
fi

# Verifica se há relatório XML
if [ -f "$TEST_RESULTS_DIR/pytest-report_$TIMESTAMP.xml" ]; then
    print_message "$YELLOW" "📄 Relatório XML: pytest-report_$TIMESTAMP.xml"
fi

exit $EXIT_CODE
