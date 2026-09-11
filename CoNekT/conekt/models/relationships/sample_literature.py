from conekt import db

from conekt.models.sample import Sample
from conekt.models.literature import LiteratureItem


class SampleLitAssociation(db.Model):
    __tablename__ = 'sample_literature'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id', ondelete='CASCADE'))
    literature_id = db.Column(db.Integer, db.ForeignKey('literature.id', ondelete='CASCADE'))
    species_id = db.Column(db.Integer, db.ForeignKey('species.id', ondelete='CASCADE'))
    literature_information = db.relationship('LiteratureItem', backref=db.backref('lit_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')

    def __init__(self, sample_id, literature_id, species_id):
        self.sample_id = sample_id
        self.literature_id = literature_id
        self.species_id = species_id
