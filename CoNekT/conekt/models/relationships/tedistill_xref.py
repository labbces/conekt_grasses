from conekt import db


class TEdistillXRefAssociation(db.Model):
    __tablename__ = 'tedistill_xref'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    tedistill_id = db.Column(db.Integer, db.ForeignKey('tedistills.id', ondelete='CASCADE'))
    xref_id = db.Column(db.Integer, db.ForeignKey('xrefs.id', ondelete='CASCADE'))
