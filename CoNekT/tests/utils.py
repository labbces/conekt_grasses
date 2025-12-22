import pytest

from utils.tau import tau
from utils.entropy import entropy, entropy_from_values
from utils.jaccard import jaccard
from utils.sequence import translate
from utils.enrichment import hypergeo_cdf, hypergeo_sf, fdr_correction
from utils.expression import max_spm


def test_tau():
    assert tau([1, 0, 0, 0, 0, 0]) == 1
    assert tau([1, 1, 1, 1, 1, 1]) == 0
    assert tau([0, 0, 0, 0, 0, 0]) is None
    assert pytest.approx(tau([0, 8, 0, 0, 0, 2, 0, 2, 0, 0, 0, 0]), abs=0.01) == 0.95


def test_enrichment():
    assert pytest.approx(hypergeo_cdf(2, 3, 10, 100), abs=0.001) == 0.999
    assert pytest.approx(hypergeo_cdf(2, 6, 10, 100), abs=0.001) == 0.987

    assert pytest.approx(hypergeo_sf(2, 3, 10, 100), abs=0.001) == 0.026
    assert pytest.approx(hypergeo_sf(2, 6, 10, 100), abs=0.001) == 0.109

    assert fdr_correction([0.05, 0.06, 0.07]) == [0.07, 0.07, 0.07]


def test_entropy():
    assert entropy([1, 0, 0, 0, 0, 0]) == 0

    assert (
        entropy_from_values([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3], num_bins=4)
        == entropy([3, 3, 3, 3])
    )
    assert entropy_from_values([0, 0, 0], num_bins=4) == entropy([])


def test_expression():
    assert max_spm({"leaf": 1, "root": 0}, substract_background=False) == {
        "condition": "leaf",
        "score": 1,
    }
    assert max_spm({"leaf": 1.1, "root": 0.1}, substract_background=True) == {
        "condition": "leaf",
        "score": 1,
    }
    assert max_spm({}, substract_background=False) is None


def test_jaccard():
    assert jaccard("ab", "bc") == 1 / 3
    assert jaccard("ab", "cd") == 0
    assert jaccard("ab", "ab") == 1


def test_sequence():
    sequence = "ATGTCAGAATTATTACAGTTGCCTCCAGGTTTCCGATTTCACCCTACCGATGAAGAGCTTGTCATGCACTATCTCTGCCGCAAATGTGCCTCTCAGTCCATCGCCGTTCCGATCATCGCTGAGATCGATCTCTACAAATACGATCCATGGGAGCTTCCTGGTTTAGCCTTGTATGGTGAGAAGGAATGGTACTTCTTCTCTCCCAGGGACAGAAAATATCCCAACGGTTCGCGTCCTAACCGGTCCGCTGGTTCTGGTTACTGGAAAGCTACCGGAGCTGATAAACCGATCGGACTACCTAAACCGGTCGGAATTAAGAAAGCTCTTGTTTTCTACGCCGGCAAAGCTCCAAAGGGAGAGAAAACCAATTGGATCATGCACGAGTACCGTCTCGCCGACGTTGACCGGTCCGTTCGCAAGAAGAAGAATAGTCTCAGGCTGGATGATTGGGTTCTCTGCCGGATTTACAACAAAAAAGGAGCTACCGAGAGGCGGGGACCACCGCCTCCGGTTGTTTACGGCGACGAAATCATGGAGGAGAAGCCGAAGGTGACGGAGATGGTTATGCCTCCGCCGCCGCAACAGACAAGTGAGTTCGCGTATTTCGACACGTCGGATTCGGTGCCGAAGCTGCATACTACGGATTCGAGTTGCTCGGAGCAGGTGGTGTCGCCGGAGTTCACGAGCGAGGTTCAGAGCGAGCCCAAGTGGAAAGATTGGTCGGCCGTAAGTAATGACAATAACAATACCCTTGATTTTGGGTTTAATTACATTGATGCCACCGTGGATAACGCGTTTGGAGGAGGAGGGAGTAGTAATCAGATGTTTCCGCTACAGGATATGTTCATGTACATGCAGAAGCCTTACTAG"
    translation = "MSELLQLPPGFRFHPTDEELVMHYLCRKCASQSIAVPIIAEIDLYKYDPWELPGLALYGEKEWYFFSPRDRKYPNGSRPNRSAGSGYWKATGADKPIGLPKPVGIKKALVFYAGKAPKGEKTNWIMHEYRLADVDRSVRKKKNSLRLDDWVLCRIYNKKGATERRGPPPPVVYGDEIMEEKPKVTEMVMPPPPQQTSEFAYFDTSDSVPKLHTTDSSCSEQVVSPEFTSEVQSEPKWKDWSAVSNDNNNTLDFGFNYIDATVDNAFGGGGSSNQMFPLQDMFMYMQKPY*"

    assert translate(sequence) == translation
    assert translate(sequence, trim=False) == translation
    assert translate("AAA" + sequence, trim=False) != translation
    assert translate("AAA" + sequence, trim=True) == translation
    assert translate(sequence + "AAA", return_on_stop=False) != translation
    assert translate(sequence + "AAA", return_on_stop=False) == translation + "K"
    assert translate(sequence + "AAA", return_on_stop=True) == translation
    assert translate("ATGSEB") == "MX"
