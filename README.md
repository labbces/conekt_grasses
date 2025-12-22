# CoNekT Grasses

## What is CoNekT Grasses?

CoNekT Grasses derives from CoNekT (Co-expression Network Toolkit), described in Proost *et al*. 2018 ([https://doi.org/10.1093/nar/gky336](https://doi.org/10.1093/nar/gky336)), an interactive and open-source web server dedicated to grasses expression data analysis.


## Tutorials

  * [The Basics](CoNekT/docs/build/tutorials/001_basics.md)
  * [Expression profiles, heatmaps and specificity](CoNekT/docs/build/tutorials/002_expression_profiles.md)
  * [Gene Families and Phylogenetic trees](CoNekT/docs/build/tutorials/003_gene_families_trees.md)
  * [Comparing specificity](CoNekT/docs/build/tutorials/004_compare_specificity.md)
  * [Coexpression Networks and Clusters](CoNekT/docs/build/tutorials/005_coexpression_networks_clusters.md)


## Quick Start for developers

CoNekT Grasses currently requires Python 3.8. To install Python 3.8 execute the following codes:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.8
```
To install MariaDB execute the following codes:

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
pip3 install virtualenv
```

To set up the environment from the root directory of the repository, run:

```bash
virtualenv --python=python3.8 CoNekT
source CoNekT/bin/activate
sudo apt-get install python3.8-dev libmysqlclient-dev apache2 apache2-dev libapache2-mod-wsgi-py3
pip3 install -r requirements.txt
```

Exclude .gitignore from the virtual environment for compatibility:

```bash
rm CoNekT/.gitignore
```

Next steps:

 * [Build the database](CoNekT/docs/source/conekt_grasses_mariadb.md)
 * [Running tests](CoNekT/docs/source/run_tests.md)

## Database Migrations with Alembic

CoNekT Grasses uses Alembic for database schema versioning and migrations. Alembic allows you to track changes to the database structure over time and apply them consistently across different environments.

For detailed information on creating and applying migrations, see the [Alembic Migration Guide](https://github.com/Lab-LBMM/projetos_desenvolvimento_web/blob/main/Docs/MIGRATIONS.md).

## Testing with Pytest

The project uses pytest as the testing framework with comprehensive integration tests for all major features. Tests are organized to cover website routes, data loading functions, and model operations.

For complete instructions on running tests, creating new tests, and understanding the testing structure, see the [Pytest Guide](https://github.com/Lab-LBMM/projetos_desenvolvimento_web/blob/main/Docs/PYTEST.md).

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

 * Dr. Renato Augusto Correa dos Santos (dev leader)
 * Prof. Dr. Diego M. Riaño-Pachón (group leader)
 * Gustavo Lelli
 * João Leite Novoletti
 * Andreza Mattoso da Cunha
 * Paulo Turquetti


## Previous collaborators

 * David Texeira Ferraz
 * Bianca Santos Pastos
 * Arthur Shuzo Owtake Cardoso
 * Luis Bezerra
 * Felipe Vaz Peres
 * Jorge Muñoz


## Licenses

 * [LabBCES LICENSE](LICENSE)
 * [Original CoNekT license (Dr. Sebastian Proost)](LICENSE_CoNekT.md)
