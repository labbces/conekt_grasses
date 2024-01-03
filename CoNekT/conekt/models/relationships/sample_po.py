from conekt import db

class SamplePOAssociation(db.Model):
    __tablename__ = 'sample_po'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id', ondelete='CASCADE'))
    po_id = db.Column(db.Integer, db.ForeignKey('plant_ontology.id', ondelete='CASCADE'))
    po_branch = db.Column(db.Enum('po_anatomy', 'po_dev_stage'))  # select the type of po (anatomy/dev stage)
    species_id = db.Column(db.Integer, db.ForeignKey('species.id', ondelete='CASCADE'))

    species = db.relationship('Species', backref=db.backref('po_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')
    po_information = db.relationship('PlantOntology', backref=db.backref('po_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')

    def __init__(self, sample_id, po_id):
        self.sample_id = sample_id
        self.po_id = po_id
