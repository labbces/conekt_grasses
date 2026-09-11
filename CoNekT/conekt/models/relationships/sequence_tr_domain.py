from conekt import db

class SequenceTRDomainAssociation(db.Model):
    __tablename__ = 'sequence_tr_domain'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id', ondelete='CASCADE'))
    domain = db.Column(db.Text, default=None)
    query_start = db.Column(db.Integer, default=None)
    query_end = db.Column(db.Integer, default=None)

    sequence = db.relationship('Sequence', backref=db.backref('tr_domain_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')

    def __init__(self, sequence_id, domain, query_start, query_end):
        self.sequence_id = sequence_id
        self.domain = domain
        self.query_start = query_start
        self.query_end = query_end