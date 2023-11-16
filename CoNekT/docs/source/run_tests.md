Install apache and mod_wsgi for python 3, and the libmysql library:

    sudo apt-get install python3.8-dev libmysqlclient-dev apache2 apache2-dev libapache2-mod-wsgi-py3

**These instructions are the same for setting up the real application. You will not need to run these apt-get install commands again if you begin from the unit tests!!**

# Configuring a MySQL/MariaDB database for the unit tests

User `conekt_grasses_testadmin` and database `conekt_grasses_test_db` are needed for the unit tests. The user needs to have all privileges on the database.

```
CREATE USER conekt_grasses_testadmin@localhost IDENTIFIED BY 'password1';
CREATE DATABASE conekt_grasses_test_db CHARACTER SET latin1 COLLATE latin1_general_ci;
GRANT INDEX, CREATE, DROP, SELECT, UPDATE, DELETE, ALTER, EXECUTE, INSERT on conekt_grasses_test_db.* TO conekt_grasses_testadmin@localhost;
GRANT FILE on *.* TO conekt_grasses_testadmin@localhost;
```

# A Flask configuration file is needed

`tests/` folder comes with a configutation file (`config.py`) similar to the main application configutation file.

The following line in the tests config file indicates that the unit tests will use the `conekt_grasses_test_db` database:

```
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://conekt_grasses_testadmin:password1@localhost/conekt_grasses_test_db'
```

## BLAST 