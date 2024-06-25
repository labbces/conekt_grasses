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

To install Python 3.8 execute the following codes:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.8
```
To install MariaDB execute the followin codes:

```bash
sudo apt update 
sudo apt install mariadb-server
sudo mysql_secure_installation
```

Dependencies are usually installed using `apt` and `pip`:


```bash
sudo apt install python3.8-venv python3.8-dev
python3.8 -m ensurepip --default-pip
python3.8 -m pip install --upgrade pip setuptools wheel
pip3.8 install virtualenv
```

To set up the environment from the root directory of the repository, run:

```bash
virtualenv --python=python3.8 CoNekT
source CoNekT/bin/activate
sudo apt-get install python3.8-dev libmysqlclient-dev apache2 apache2-dev libapache2-mod-wsgi-py3
pip install -r requirements.txt
```

Next steps:

 * [Running tests](https://github.com/labbces/conekt_grasses/blob/main/CoNekT/docs/source/run_tests.md)
 * [Build the datatase](https://github.com/labbces/conekt_grasses/blob/main/CoNekT/docs/source/connect_mysql.md)
 * [Add data to CoNekT Grasses](https://github.com/labbces/conekt_grasses/blob/main/CoNekT/docs/source/building_conekt.md)

## Building documentation with Sphinx


Documentation can be generated using Sphinx.

To generate the documentation, run:

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
 * Bianca Santos Pastos
 * Arthur Shuzo Owtake Cardoso
 * Prof. Dr. Diego M. Riaño-Pachón (group leader)


## Collaborators

 * Felipe Vaz Peres
 * Jorge Muñoz


## Previous collaborators

 * David Texeira Ferraz


## Licenses

 * [LabBCES LICENSE](LICENSE)
 * [Original CoNekT license (Dr. Sebastian Proost)](LICENSE_CoNekT.md)
