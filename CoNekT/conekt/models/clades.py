from conekt import db
from conekt.models.species import Species

import json
import newick

SQL_COLLATION = 'NOCASE' if db.engine.name == 'sqlite' else ''


class Clade(db.Model):
    __tablename__ = 'clades'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50, collation=SQL_COLLATION), unique=True, index=True)
    species = db.Column(db.Text(collation=SQL_COLLATION))
    species_count = db.Column(db.Integer)
    newick_tree = db.Column(db.Text)

    families = db.relationship('GeneFamily', backref='clade', lazy='dynamic')
    interpro = db.relationship('Interpro', backref='clade', lazy='dynamic')

    def __init__(self, name, species, tree):
        self.name = name
        self.species = json.dumps(species)
        self.species_count = len(species)
        self.newick_tree = tree

    def __repr__(self):
        return str(self.id) + ". " + self.name

    @property
    def newick_tree_species(self):
        """
        Returns a Newick tree with the species present in the current clade.

        :return: Newick tree (string) with species for the current clade
        """
        species = {s.code: s.name for s in Species.query.all()}

        tree = newick.loads(self.newick_tree)[0]

        for code, name in species.items():
            node = tree.get_node(code)
            if node is not None:
                node.name = name

        return newick.dumps([tree])