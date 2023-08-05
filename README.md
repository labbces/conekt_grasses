# CoNekT Grasses

## What is CoNekT Grasses?

CoNekT Grasses derives from CoNekT, described in Proost *et al*. 2018. ( [https://doi.org/10.1093/nar/gky336](https://doi.org/10.1093/nar/gky336) )


## Tutorials

  * [The Basics](CoNekT/docs/build/tutorials/001_basics.md)
  * [Expression profiles, heatmaps and specificity](CoNekT/docs/build/tutorials/002_expression_profiles.md)
  * [Gene Families and Phylogenetic trees](CoNekT/docs/build/tutorials/003_gene_families_trees.md)
  * [Comparing specificity](CoNekT/docs/build/tutorials/004_compare_specificity.md)
  * [Coexpression Networks and Clusters](CoNekT/docs/build/tutorials/005_coexpression_networks_clusters.md)


## Quick Start for developers

CoNekT Grasses currently requires:
 * Python 3.8

To set up the environment from the root directory of the repository, run:

```bash
virtualenv --python=python3.8 CoNekT/CoNekT/
source CoNekT/CoNekT/bin/activate
pip install -r requirements.txt
```

Documentation can be generated using Sphinx. To generate the documentation, run:

```bash
cd CoNekT/docs/
sphinx-build -b html source/ build/
```

Note that we changed the default Sphinx builder to use the Markdown parser. This is done by adding the following line to `conf.py` file in the `CoNekT/docs` folder:

```
extensions = ["myst_parser"]
```


## Developers

 * Dr. Renato Augusto Correa dos Santos
 * David Texeira Ferraz
 * Bianca Santos Pastos
 * Arthur Shuzo Owtake Cardoso
 * Prof. Dr. Diego M. Riaño-Pachón (group leader)


## Collaborators

 * Felipe Vaz Peres
 * Jorge Muñoz


## Licenses

 * [LabBCES LICENSE](LICENSE)
 * [Original CoNekT license (Dr. Sebastian Proost)](LICENSE_CoNekT.md)