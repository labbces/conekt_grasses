# Etapas - Pré-processamento

## Recuperação dos dados brutos de processamento

Verificar no artigo os dados a serem usados através do código Short Read Archive(SRA) do NCBI, que começa com SRR, por ex SRR1979656.

Os arquivos de sequenciamento de rna estão no formato fastq.

### Download com ffq e wget

Caso não tena o ffq instalado, para instala-lo use

``` bash
pip install ffq
```
O ffq é uma biblioteca de python que é usada para fazer o download do arquivo SRR.

``` bash
ffq -o SRR1979656.json SRR1979656
```
### Download com sratoolkit 
