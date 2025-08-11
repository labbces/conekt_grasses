from conekt import db

SQL_COLLATION = 'NOCASE' if db.engine.name == 'sqlite' else ''


class ConditionTissue(db.Model):
    __tablename__ = 'conditions_tissue'
    id = db.Column(db.Integer, primary_key=True)
    species_id = db.Column(db.Integer, db.ForeignKey('species.id', ondelete='CASCADE'))
    data = db.Column(db.Text)
    description = db.Column(db.Text)

    expression_specificity_method_id = db.Column(db.Integer,
                                                 db.ForeignKey('expression_specificity_method.id', ondelete='CASCADE'),
                                                 index=True)

    in_tree = db.Column(db.SmallInteger, default=0)
