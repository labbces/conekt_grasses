from conekt import db

class SamplePECOAssociation(db.Model):
    __tablename__ = 'sample_peco'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id', ondelete='CASCADE'))
    peco_id = db.Column(db.Integer, db.ForeignKey('plant_experimental_conditions_ontology.id', ondelete='CASCADE'))
    species_id = db.Column(db.Integer, db.ForeignKey('species.id', ondelete='CASCADE'))

    species = db.relationship('Species', backref=db.backref('peco_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')

    def __init__(self, sample_id, peco_id):
        self.sample_id = sample_id
        self.peco_id = peco_id