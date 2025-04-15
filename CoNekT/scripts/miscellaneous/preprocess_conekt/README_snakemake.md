# Etapas - Pré-processamento

## Metadados das amostras

Verificar no artigo e no NCBI quais as informações relacionadas as amostras. Para isso realizo o seguinte procedimento:

1- pesquiso o SRR no NCBI;
2- clico no bioproject;
3- procuro por uma tabela(PROJECT DATA) e clico no valor que está na frente do 'SRA Experiments';
4- na página que irá abrir, clico em 'Send to', clico em 'file', e logo abaixo na aba que irá abrir, clico em 'Format'
   depois em 'Runinfo' e para finalizar clico em 'Create file'.
5- no arquivo que foi gerado, abro e vou até a coluna 'Library Strategy' e deleto todas as linhas que não contém 'RNA-SEQ'

## Recuperação dos dados brutos de processamento

Verificar no artigo os dados a serem usados através do código Short Read Archive(SRA) do NCBI, que começa com SRR, por ex SRR1979656.

Os arquivos de sequenciamento de rna estão no formato fastq.

### Download com ffq e wget

Caso não tenha o ffq instalado, para instala-lo use

``` bash
pip install ffq
```
O ffq é uma biblioteca de python que é usada para fazer o download do arquivo SRR.

``` bash
ffq -o SRR1979656.json SRR1979656
```
### Download com sratoolkit 

Caso não tenha faça o download compatível com seu sistema operacional(https://github.com/ncbi/sra-tools/wiki/01.-Downloading-SRA-Toolkit).

Com o programa instalado e configurado baixe os dados desejados usando o comando 'prefetch' mais o código de SRR desejado. Com o arquivo baixado rode o comando 'fasterq-dump' para converter as Runs pré-buscadas do formato SRA compactado para o formato fastq.

