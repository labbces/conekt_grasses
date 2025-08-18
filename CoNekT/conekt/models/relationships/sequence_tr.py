from conekt import db

class SequenceTRAssociation(db.Model):
    __tablename__ = 'sequence_tr'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id', ondelete='CASCADE'))
    tr_id = db.Column(db.Integer, db.ForeignKey('transcription_regulator.id', ondelete='CASCADE'))

    sequence = db.relationship('Sequence', backref=db.backref('tr_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')

    tr = db.relationship('TranscriptionRegulator', backref=db.backref('sequence_associations',
                                                  lazy='dynamic',
                                                  passive_deletes=True), lazy='joined')

    def __init__(self, sequence_id, tr_id, query_start, query_end):
        self.sequence_id = sequence_id
        self.tr_id = tr_id
        self.query_start = query_start
        self.query_end = query_end