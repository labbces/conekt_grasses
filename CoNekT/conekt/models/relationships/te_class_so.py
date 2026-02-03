from conekt import db


class TEClassSOAssociation(db.Model):
    __tablename__ = 'te_class_so'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    te_class_id = db.Column(db.Integer, db.ForeignKey('te_classes.id', ondelete='CASCADE'))
    sequence_ontology_id = db.Column(db.Integer, db.ForeignKey('sequence_ontologies.id', ondelete='CASCADE'))
    evidence_code = db.Column(db.Enum('IEA', 'TAS', 'NAS', 'IC', 'ND', 'RCA', 'NR', name='evidence_codes'),
                               default='IEA', index=True)
    
    # Additional metadata for the association
    confidence = db.Column(db.Float)  # Confidence score for the association
    source = db.Column(db.String(255))  # Source of the annotation (e.g., RepeatMasker, TEsorter, etc.)

    te_class = db.relationship('TEClass', backref=db.backref('so_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')
    sequence_ontology = db.relationship('SequenceOntology', backref=db.backref('te_class_associations',
                                                                                lazy='dynamic',
                                                                                passive_deletes=True), lazy='joined')


# Keep te_class_so for backward compatibility
te_class_so = TEClassSOAssociation.__table__