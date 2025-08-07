from conekt import db

SQL_COLLATION = 'NOCASE' if db.engine.name == 'sqlite' else ''


class LiteratureItem(db.Model):
    __tablename__ = 'literature'
    id = db.Column(db.Integer, primary_key=True)
    qtd_author = db.Column(db.Integer, nullable=False)
    author_names = db.Column(db.String(100, collation=SQL_COLLATION), nullable=False)
    title = db.Column(db.String(250, collation=SQL_COLLATION), nullable=False)
    public_year = db.Column(db.Integer, nullable=False)
    doi = db.Column(db.String(100, collation=SQL_COLLATION), nullable=False,
                    unique=True)

    def __init__(self, qtd_author, author_names, title, public_year, doi):
        self.qtd_author = qtd_author
        self.author_names = author_names
        self.title = title
        self.public_year = public_year
        self.doi = doi

    def __repr__(self):
        return str(self.id) + ". " + (f'{self.author_names} ({self.public_year})')
