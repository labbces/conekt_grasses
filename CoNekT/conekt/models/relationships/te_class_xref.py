from conekt import db


class TEClassXRefAssociation(db.Model):
    __tablename__ = 'te_class_xref'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    te_class_id = db.Column(db.Integer, db.ForeignKey('te_classes.id', ondelete='CASCADE'))
    xref_id = db.Column(db.Integer, db.ForeignKey('xrefs.id', ondelete='CASCADE'))

    te_class = db.relationship('TEClass', backref=db.backref('xref_associations',
                                                               lazy='dynamic',
                                                               passive_deletes=True), lazy='joined')

    xref = db.relationship('XRef', backref=db.backref('te_class_associations',
                                                        lazy='dynamic', passive_deletes=True), lazy='joined')
