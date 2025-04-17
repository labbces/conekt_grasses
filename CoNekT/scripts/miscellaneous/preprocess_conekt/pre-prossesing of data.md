# Steps Pré -Processing

## Sample metadata

Check in article and NCBI what information listed to samples. For this I perform the following procedure:

1-Research SRR in the NCBI;
2-Click on Bioproject;
3-Procedure by a table (project data) and click on the value in front of the MRs experiments;
4-In page that will open, click 'Send To', click 'File', and below the tab that will open, click 'format' then 'Runinfo' and to finish click on 'Create File'.
5-In the file that was generated, check the 'Library Strategy' column and delete all lines that do not contain 'RNA-SEQ'

## Gross Processing Data Recovery

Check in the article the data to be used through the NCBI Short Read Archive Code, which starts with SRR, by ex SRR1979656.
RNA sequencing files are in Fastq format.

### Download with FFQ and WGET

If you do not have FFQ installed, to install it, use

```bash

pip install ffq

```
ffq is a Python library that is used to download the SRR file.

```bash

ffq -o SRR1979656.json SRR1979656

```
### Download with Sratoolkit 

If you do not have the download compatible with your operating system (https://github.com/ncbi/sra-tools/wiki/01.-downloading-sra-toolkit).

With the program installed and configured download the desired data using the 'FASTERQ-Dump' command plus the desired SRR code. 

