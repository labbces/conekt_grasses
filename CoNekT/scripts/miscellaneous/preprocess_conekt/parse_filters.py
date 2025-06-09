#!/usr/bin/env python

import sys
print("Python executable:", sys.executable)

import pandas as pd
print("Pandas version:", pd.__version__)

import argparse

parser = argparse.ArgumentParser(prog='parse_filters.py', description='Parse CoNekT Bioenergy snakemake pipeline filters', add_help=True)
parser.add_argument('--accessions', dest='accessions', metavar='<accesions csv file>', help='file containing SRA IDs', required=True)
parser.add_argument('--paired_runlist', dest='paired_runlist', metavar='<paired runlist csv file>', help='file containing only paired accessions', required=True)
parser.add_argument('--filter_stats', dest='filter_stats', metavar='<filter stats file>', help='file containing only filtered accessions', required=True)

args = parser.parse_args()
accessions = args.accessions
paired_runlist = args.paired_runlist
filter_stats = args.filter_stats

#Trocar virgula por \n no acessions (dentro do shell snakemake)
sample_column = ['Sample']
download = pd.read_csv(accessions, header=None, names=sample_column)

#Trocar virgula por \n no paired_runlist (dentro do shell snakemake)
filter1 = pd.read_csv(paired_runlist, header=None, names=sample_column)

#Trocar tab por virgula no filter_stats
filter_columns = ['Sample', 'Mapping Rate', 'Perc Low TPM']
filter2 = pd.read_csv(filter_stats, header=0, names=filter_columns)

### Essa parte esta errada. A ordem das samples nao esta sendo mantida no arquivo final
#gerar indice com todos samples
#download['Sample'] = download.Sample
#download['Downloaded'] = download.Sample.isin(filter2.Sample)
#download['Paired'] = download.Sample.isin(filter1.Sample)

#join indices 
#download['Mapping Rate'] = filter2['Mapping Rate']
#download['Perc Low TPM'] = filter2['Perc Low TPM']

#print(download)
#download.to_csv('preliminar_report.tsv')

### Corrigindo merge das samples
merged = pd.merge(download, filter2, on='Sample', how='left')
merged['Downloaded'] = merged['Sample'].isin(filter2['Sample'])
merged['Pass Filter'] = merged['Sample'].isin(filter1['Sample'])

merged.to_csv('preliminar_report.tsv', index=False)
print(merged)
