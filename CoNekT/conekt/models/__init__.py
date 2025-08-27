from conekt import db

# Base model for Flask Migrate (DO NOT MODIFY)
class Base(db.Model):
    __abstract__ = True