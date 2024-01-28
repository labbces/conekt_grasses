#!/usr/bin/env python3

import argparse

parser = argparse.ArgumentParser(description='Generates a file with GOs for genes in InterProScan results')
parser.add_argument('--interproscan', type=str, metavar='Svi_interproscan.tsv',
                    dest='interproscan_file',
                    help='The InterProScan file to use',
                    required=True)
parser.add_argument('--out_go', type=str, metavar='Svi_go.tsv',
                    dest='go_outfile',
                    help='The out file to add GOs to CoNekT Grasses',
                    required=True)

args = parser.parse_args()
interproscan = args.interproscan_file
go_file = args.go_outfile

gene2go = {}

go_file_obj = open(go_file, 'w')

# Read the InterProScan file
with open(interproscan, 'r') as f:
    for line in f:
        if line.startswith('#'):
            continue
        gene, go_list = line.split('\t')[0], line.split('\t')[13]
        if go_list.startswith('GO:'):
            go_list_split = go_list.split('|')
            for go in go_list_split:
                go = go.replace('(PANTHER)','')
                go = go.replace('(InterPro)','')
                if gene not in gene2go.keys():
                    gene2go[gene] = [go]
                    go_file_obj.write(f'{gene}\t{go}\tISM\n')
                else:
                    if go not in gene2go[gene]:
                        gene2go[gene].append(go)
                        go_file_obj.write(f'{gene}\t{go}\tISM\n')