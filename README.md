# CoNekT Grasses

## What is CoNekT Grasses?

CoNekT Grasses derives from CoNekT, described in Proost *et al*. 2018. ( [https://doi.org/10.1093/nar/gky336](https://doi.org/10.1093/nar/gky336) )


## Tutorial
# CoNekT Grasses Installation and Population

## 1. Preparação do ambiente

1. Crie um diretório para o CoNekT.
2. Baixe o CoNekT do GitHub:
   ```bash
   git clone https://github.com/labbces/conekt_grasses.git
   ```
3. Crie o ambiente virtual **CoNeKT** seguindo as instruções em [Quick Start for developers](https://https://github.com/labbces/conekt_grasses/blob/working_install/README.md#quick-start-for-developers).
4. Crie o ambiente virtual **Populate** conforme o [README_populate](https://github.com/labbces/conekt_grasses/blob/main/CoNekT/scripts/README_populate.md#setting-up-the-virtual-environment)


## 2. Configuração do banco de dados

1. Siga as instruções em [Build the database](https://github.com/labbces/conekt_grasses/blob/main/CoNekT/docs/source/connect_mysql.md) no GitHub para criar o banco.
2. Edite o arquivo de configuração do MariaDB:
   ```bash
   sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
   ```
3. Descomente ou adicione a linha:
   ```ini
   max_allowed_packet = 512M
   ```
4. Reinicie o MariaDB:
   ```bash
   sudo systemctl restart mariadb
   ```
5. Verifique se funcionou:
   ```sql
   SHOW VARIABLES LIKE 'max_allowed_packet';
   ```
   → O valor deve ser **536870912** (512 MB em bytes).

## 3. Organização dos dados

1. No script `populate_conekt_grasses.sh`, altere estas variáveis:
   - `BASE_DIR`
   - `SCRIPTS_DIR`
   - `DATA_DIR`
   - `SPECIES_ARRAY` (coloque as espécies que deseja, ex: `Scp1`)
2. Prepare o arquivo `info_species.tsv` com o caminho dos seus dados:
   ```
   species_code	data_path
   Scp1	/home/seu_usuario/dados/Scp1
   ```
Atenção: O nome dos dados deve ser o mesmo na pasta do diretório, na variável SPECIES ARRAY  e no arquivo info_species.tsv

3. **Verifique o arquivo de anotação (`expression_annotation.txt`):**
   - Deve ter **9 colunas separadas por tabs**.
   - A coluna `Replicate` deve conter **apenas números inteiros** (1, 2, 3...), **nunca letras** (B, M, P...).

## 4. Execução do pipeline

Execute o pipeline:
```bash
./populate_conekt_grasses.sh
```

- Se tudo correr bem, você verá:  
  `Pipeline concluído com sucesso!`
- **Atenção:** Para cana-de-açúcar (`Scp1`), o pipeline pode levar **24–72 horas**, dependendo do hardware.
- O cálculo de especificidade é a etapa mais demorada — não interrompa!

## 5. Dicas de monitoramento

- Use `htop` ou `watch -n 2 free -h` para monitorar uso de CPU e memória.
- Verifique o progresso pelas mensagens:
  ```
  → Processed 10000 profiles
  → Committed 400 specificities
  ```

## 6. Adicionando novos dados depois

Os scripts encontram-se na pasta: CoNekT/scripts/add

- Para **adicionar mais perfis de expressão da mesma espécie**, use apenas:
  ```bash
  python add/add_expression_data.py --species_code Scp1 ...
  ```
- Para **adicionar uma nova espécie**, repita as etapas de:
  - `add_species.py`
  - `add_gene_descriptions.py`
  - `add_interproscan.py`, `add_go.py`, `add_cazymes.py`
  - `add_expression_data.py`
  - (opcional) `calculate_specificities_fast.py`
  - `update_counts.py`


 
## Quick Start for developers

CoNekT Grasses currently requires:
 * Python 3.8

To install Python 3.8 execute the following codes:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.8
```

Dependencies are usually installed using `apt` and `pip`:


```bash
apt install python3.8-venv python3.8-dev
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
 * Prof. Dr. Diego M. Riaño-Pachón (group leader)


## Collaborators

 * Felipe Vaz Peres
 * Jorge Muñoz


## Previous collaborators

 * David Texeira Ferraz
 * Bianca Santos Pastos
 * Arthur Shuzo Owtake Cardoso


## Licenses

 * [LabBCES LICENSE](LICENSE)
 * [Original CoNekT license (Dr. Sebastian Proost)](LICENSE_CoNekT.md)
