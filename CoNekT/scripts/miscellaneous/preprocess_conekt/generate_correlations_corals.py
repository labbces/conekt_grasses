#!/usr/bin/env python

import argparse
import pandas as pd

from corals.threads import set_threads_for_external_libraries
set_threads_for_external_libraries(n_threads=1)
import numpy as np
from corals.correlation.full.default import cor_full
from corals.correlation.utils import derive_pvalues, multiple_test_correction

parser = argparse.ArgumentParser(description='Generate correlations with corALS')
parser.add_argument('--expression_matrix', type=str, dest='expression_file',
                    help='Expression file', metavar="matrix.tsv",
                    required=True)
parser.add_argument('--output_network', type=str, dest='output_network',
                    help='Network file', metavar="network.txt",
                    required=False)
args = parser.parse_args()

matrix_file = args.expression_file
output_network = args.output_network

expression_matrix = pd.read_csv(matrix_file, sep="\t", index_col=0)
expression_matrix_transposed = expression_matrix.transpose()

expression_matrix_pearson_result = cor_full(expression_matrix_transposed, correlation_type="pearson")

expression_matrix_pearson_result.to_csv(output_network, sep="\t")
