# CoNekT Grasses

## Quick Start

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

## LICENSES

 * [LabBCES LICENSE](LICENSE)
 * [Original CoNekT license (Dr. Sebastian Proost)](LICENSE_CoNekT.md)