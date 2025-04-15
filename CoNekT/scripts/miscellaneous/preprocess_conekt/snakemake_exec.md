# Antes de começar

Crie uma pasta com o nome do projeto/espécie que vocẽ está trabalhando.

## 1. Clone este repositório

Na pasta que você criou, clone o repositório abaixo. 

git clone https://github.com/felipevzps/conekt-grasses-snakemake-pipeline.git
cd conekt-grasses-snakemake-pipeline * colocar o link correto

## 2. Instale e configure o ambiente virtual

Na pasta que você criou, instale e configure o ambiente virtual.

# installing conda env - this might take some time...
conda env create -n conekt-grasses-snakemake-pipeline -f environment.yaml

# activating the environment
conda activate conekt-grasses-snakemake-pipeline

## 3. Configurar caminhos de software no config.yaml

Antes de executar o pipeline, revise o config.yaml. Alguns caminhos na configuração são específicos do usuário, enquanto outros são específicos do cluster. Portanto, sempre que um novo usuário pretende executar o pipeline, é necessário ajustar os caminhos de software de acordo.

## 4. Configurar o arquivo Snakefile

No arquivo, você deverá ajustar o nome de suas amostras e do transcriptoma de referência.

## 4. Execute o pipeline

Comece com uma execução de teste para garantir que tudo esteja configurado corretamente:

snakemake -np

Esse comando listará todas as etapas planejadas, desde o download de leituras brutas até a geração de matrizes de quantificação e relatórios.

Se estiver tudo certo, execute o pipeline:

qsub Snakefile.sh

