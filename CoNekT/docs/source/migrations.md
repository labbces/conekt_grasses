# Practical Guide: Using Alembic for Database Migrations

## 1. What is Alembic?

Alembic is a database migration tool for Python, created by the same developers as SQLAlchemy. It allows us to modify and version our database schema in a programmatic and controlled way.

Each change (such as creating a table or adding a column) is encapsulated in a "migration script". These scripts can be applied (`upgrade`) or reverted (`downgrade`), ensuring that all environments (development, production, etc.) are always in sync.

---

## 2. Installation and Initial Setup

To start using Alembic in the project, follow these steps.

**a. Installation:**  
Alembic is already installed in the project dependencies. Flask-Migrate, which is a Flask extension to manage database migrations, depends on Alembic.

**b. Created File Structure:**  
The `init db` command executed during database creation generates the following structure:
- **`migrations/`**: Main directory.
- **`migrations/env.py`**: Configuration script that runs whenever Alembic is invoked. This is where we configure the database connection.
- **`migrations/script.py.mako`**: Template used to generate new migration scripts.
- **`migrations/versions/`**: This directory will contain all our migration scripts.
- **`migrations/alembic.ini`**: Main Alembic configuration file.

**d. Configuring the Database Connection:**  
1. Open the `alembic.ini` file.
2. Add the `sqlalchemy.url` line between `[alembic]` and `[loggers]` and point it to your database.
    ```ini
    sqlalchemy.url = mysql+pymysql://<db_admin>:<db_password>@localhost/<db_name>
    ```
---

## 3. Creating and Applying Migrations

This is the main workflow for any schema change.

**Step 1: Modify Your SQLAlchemy Models**  
Make the desired changes to your model classes. For example, add a new column to a table.

**Step 2: Generate the Migration Script (Autogenerate)**  
Use the `flask db migrate` command. Alembic will compare your models with the current state of the database and generate the script automatically.

```bash
# The -m flag is required and describes the change
flask db migrate -m "Add name column to species table"
```
A new file will be created in `migrations/versions/`, containing the `upgrade()` and `downgrade()` functions.

**Step 3: Review the Generated Script (VERY IMPORTANT!)**
- **Never blindly trust the automatically generated file.** Open the generated file and check if:
    - The operations (`op.add_column`, `op.create_table`, etc.) are correct.
    - The `downgrade()` function perfectly reverts what `upgrade()` does.
    - There are no unexpected operations that could cause data loss (such as an `op.drop_table`).

**Step 4: Apply the Migration**  
Run the `upgrade` command to apply the new migration (and any others pending) to the database.

```bash
# 'head' means apply up to the latest version
alembic upgrade head
```

**Step 5: Commit the Changes**  
Add both the model change and the new migration script to Git. They should be committed together, as they represent a single logical change.
```bash
git add conekt/models/species.py migrations/versions/20250823_add_name_column_to_species_table.py
git commit -m "feat: Add name column to species table"
```

---

## 4. Essential Commands

* **View history:**
    ```bash
    flask db history
    ```

* **View current version:**
    ```bash
    flask db current
    ```

* **Revert the last migration:**
    ```bash
    flask db downgrade
    ```

* **Revert all migrations (careful!):**
    ```bash
    flask db downgrade base
    ```

---

## 5. Best Practices

* **One Change per Migration:** Keep migrations small and focused on a single logical change. This makes debugging and reverting easier.
* **Descriptive Names:** The message (`-m "..."`) is crucial. It becomes part of the file name and history. Be clear and concise.
* **Never Edit Old Migrations:** Once a migration has been applied in shared environments (like `main`), do not edit it. If you need to fix something, create a *new* migration for the fix.
* **Work with Branches:** If `main` received new migrations while you were on a branch, rebase your branch before generating your own migration. This avoids "head" conflicts (multiple latest migrations).
* **Rename Migration Files:** Files created in `migrations/versions/` can be renamed, and it's a good idea to keep chronological order in the file names, for example: ```ab55d9ddb915_add_name_column_to_species_table.py``` -> ```20250823_add_name_column_to_species_table.py
```