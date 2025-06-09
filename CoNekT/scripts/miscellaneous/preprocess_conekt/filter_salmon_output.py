#!/usr/bin/env python

import os
import json
import argparse
import csv

good_quality_samples = []
seqtype="PAIRED"

parser = argparse.ArgumentParser(prog='filter_salmon_output.py', description='filter reads from salmon output (percent mapped and low tpm)', add_help=True)
parser.add_argument('--genotype', dest='genotype', metavar='<genotype id>', help='genotype id', required=True)
parser.add_argument('--stranded_samples', dest='stranded_samples', metavar='<stranded samples file>', help='stranded samples file', required=True)

args = parser.parse_args()
genotype = args.genotype
stranded_samples = args.stranded_samples

paired_samples_file = open(stranded_samples, 'r')
paired_samples_list = list(csv.reader(paired_samples_file, delimiter=","))

out_file = open(genotype + '_' + seqtype + '_filter_stats.txt', 'a')
out_file.write(f'Sample\tMapping Rate\tPerc Low TPM\n')
out_file.close()

for path2salmon in os.listdir('datasets_'+ genotype +'/3_salmon/quant/'):
    if path2salmon in paired_samples_list[0]:
        sample_name = path2salmon.replace('_quant','')
        f = open('datasets_'+ genotype +'/3_salmon/quant/' + path2salmon + '/aux_info/meta_info.json')
        #print("f: ", f)
        data = json.load(f)
        f2 = open('datasets_'+ genotype +'/3_salmon/quant/' + path2salmon + '/quant.sf')
        #print("f2: ", f2)
        count_transcripts = 0
        low_tpm = 0
        out_file = open(genotype + '_' + seqtype + '_filter_stats.txt', 'a')
        for line in f2:
            name, length, effectivelength, tpm, numreads = line.strip().split('\t')
            if name == 'Name':
                continue
	    # See cutoff for expression here https://www.ebi.ac.uk/gxa/FAQ.html
            if float(tpm) < 0.5:
                low_tpm+=1
            count_transcripts+=1
        perc_low_tpm = (low_tpm / count_transcripts) * 100
        out_file.write(f'{sample_name}\t{data["percent_mapped"]}\t{perc_low_tpm}\n')
        out_file.close()
        if (data['percent_mapped'] <= 1) or (perc_low_tpm >= 99.9): #40 e 60
            pass
            #print(sample_name, data['percent_mapped'], perc_low_tpm)
        else:
            good_quality_samples.append(sample_name)
            f.close()
            f2.close()

paired_samples_file.close()

print(good_quality_samples)
f3 = open(genotype + "_" + seqtype + "_runlist_LowMapping_LowReads.csv", "a")
f3.write(','.join(good_quality_samples))

#for sample in good_quality_samples:
#	print(sample)
