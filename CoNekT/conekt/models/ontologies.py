from conekt import db

SQL_COLLATION = None


class PlantOntology(db.Model):
    __tablename__ = 'plant_ontology'
    id = db.Column(db.Integer, primary_key=True)
    po_term = db.Column(db.String(10, collation=SQL_COLLATION), unique=True)
    po_class = db.Column(db.String(80, collation=SQL_COLLATION), unique=True)
    po_annotation = db.Column(db.Text)

    def __init__(self, po_term, po_class, po_annotation):
        self.po_term = po_term
        self.po_class = po_class
        self.po_annotation = po_annotation

    def __repr__(self):
        return str(self.id) + ". " + self.po_term


class PlantExperimentalConditionsOntology(db.Model):
    __tablename__ = 'plant_experimental_conditions_ontology'
    id = db.Column(db.Integer, primary_key=True)
    peco_term = db.Column(db.String(13, collation=SQL_COLLATION), unique=True)
    peco_class = db.Column(db.String(80, collation=SQL_COLLATION), unique=True)
    peco_annotation = db.Column(db.Text)

    def __init__(self, peco_term, peco_class, peco_annotation):
        self.peco_term = peco_term
        self.peco_class = peco_class
        self.peco_annotation = peco_annotation

    def __repr__(self):
        return str(self.id) + ". " + self.peco_term
