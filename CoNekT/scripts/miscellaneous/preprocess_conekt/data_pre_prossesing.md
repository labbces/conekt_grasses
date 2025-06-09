# Preprocessing steps

## Sample metadata



Check in article and NCBI what information listed to samples. 

Buscar por srr, bioproject, etc muitas vezes está na seção de informação ou disponibilidade de dados

For this I perform the following procedure:

1-Search for SRR in the NCBI; 
2-Click on Bioproject;
3-Procedure by a table (project data) and click on the value in front of the MRs experiments;
4-In page that will open, click 'Send To', click 'File', and below the tab that will open, click 'format' then 'Runinfo' and to finish click on 'Create File';
5-In the file that was generated, check the 'Library Strategy' column and delete all lines that do not contain 'RNA-SEQ'

## Recovery of Raw Sequencing Data

Check in the article the data to be used through the NCBI Short Read Archive Code, which starts with SRR, e.g., SRR1979656. RNA sequencing files are in Fastq format.

