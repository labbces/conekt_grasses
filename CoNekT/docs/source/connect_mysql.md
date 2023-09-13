# Setting up MySQL/MariaDB for CoNekT Grasses

Either use the libmysql library which needs to be installed on the machine using

    sudo apt-get install python3.8-dev libmysqlclient-dev
 
In the config file the connection needs to be set up using :

    SQLALCHEMY_DATABASE_URI = 'mysql://user:pass@ip_address/database'


In case the **libraries cannot be installed** on the machine a pure python mysql connector can be used. Install this within the virtual environment. 

    pip install PyMySQL

In the config file the connection needs to be set up using :

    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://user:pass@ip_address/database'
    
    
## Setting up the database using the MySQL CLI

First create a MySQL/MariaDB user with root:

    CREATE USER conekt_grasses_admin@localhost IDENTIFIED BY 'E,~5*;{9f{p2VGp^';

The character set and collate are important as sqlalchemy-migrate doesn't work with utf8mb4 (the default).

    CREATE DATABASE conekt_grasses_db CHARACTER SET latin1 COLLATE latin1_general_ci;
    
Give permissions to a user (conekt_grasses_admin in this example) to access the database:

    GRANT INDEX, CREATE, DROP, SELECT, UPDATE, DELETE, ALTER, EXECUTE, INSERT on conekt_grasses_db.* TO conekt_grasses_admin@localhost;

    GRANT FILE on *.* TO conekt_grasses_admin@localhost;

# Creating the Flask configuration file

First, create a copy of the configuration template file. From the repo root, run:

```bash
cd CoNekT/
cp config.template.py config.py
```

Change settings in `config.py`. **Apart from configuring paths, also change the secret key and the admin password !**

# Running the database migrations

Two commands are usually necessary, `initdb` (initialize the database) and `db init` (create a migration repository). From the repo root, run:

```bash
export FLASK_APP=run.py
cd CoNekT/
flask initdb
flask db init
```


# Running the web application

```bash
flask run
```
