from flask_caching import Cache
from flask_compress import Compress
from flask_debugtoolbar import DebugToolbarExtension
from flask_htmlmin import HTMLMIN
from flask_sqlalchemy import SQLAlchemy
from flask_whooshee import Whooshee
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlite3 import Connection as SQLite3Connection

from conekt.flask_blast import BlastThread

__all__ = ['toolbar', 'db', 'cache', 'htmlmin',
           'blast_thread', 'compress', 'whooshee', 'migrate', 'csrf']

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
        Will force sqlite contraint foreign keys
    """
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


toolbar = DebugToolbarExtension()
cache = Cache()
htmlmin = HTMLMIN()
blast_thread = BlastThread()
compress = Compress()
whooshee = Whooshee()
migrate = Migrate()
csrf = CSRFProtect()
