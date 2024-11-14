# Populating CoNekT Grasses using scripts

To do this, we need to create another virtual environment. If you are using the Conekt virtual environment, you will need to deactivate it with the commando: deactivate

```bash
deactivate
```

With the Conekt virtual environment deactivated, go to the folder:

```bash
cd Conekt/scripts
```

In the scripts folder, we will create another virtual environment.

```bash
virtualenv --python=python3.10 Populate_Conekt
```

With the Populate_Conekt virtual environment created, we will activate it.

```bash
source Populate_CoNekT/bin/activate
```

Now that the environment is active, we will install the necessary requirements:

```bash
pip install -r requirements.txt
```



