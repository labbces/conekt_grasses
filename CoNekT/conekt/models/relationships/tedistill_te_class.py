from conekt import db


class TEdistillTEClassAssociation(db.Model):
    __tablename__ = 'tedistill_te_class'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    tedistill_id = db.Column(db.Integer, db.ForeignKey('tedistills.id', ondelete='CASCADE'))
    te_class_id = db.Column(db.Integer, db.ForeignKey('te_classes.id', ondelete='CASCADE'))

    tedistill = db.relationship('TEdistill', backref=db.backref('te_class_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')
    te_class = db.relationship('TEClass', backref=db.backref('tedistill_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')


