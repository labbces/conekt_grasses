from conekt import db

class SequenceTFAssociation(db.Model):
    __tablename__ = 'sequence_tf'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id', ondelete='CASCADE'))
    tf_id = db.Column(db.Integer, db.ForeignKey('transcription_factor.id', ondelete='CASCADE'))
    query_start = db.Column(db.Integer, default=None)
    query_end = db.Column(db.Integer, default=None)

    sequence = db.relationship('Sequence', backref=db.backref('tf_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')

    tf = db.relationship('TranscriptionFactor', backref=db.backref('sequence_associations',
                                                  lazy='dynamic',
                                                  passive_deletes=True), lazy='joined')

    def __init__(self, sequence_id, tf_id, query_start, query_end):
        self.sequence_id = sequence_id
        self.tf_id = tf_id
        self.query_start = query_start
        self.query_end = query_end