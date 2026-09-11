from conekt import db

SQL_COLLATION = None


class SampleGroupAssociation(db.Model):
    __tablename__ = 'sample_groups'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id', ondelete='CASCADE'), index=True)
    group_type = db.Column(db.String(100, collation=SQL_COLLATION), unique=False)
    group_name = db.Column(db.String(100, collation=SQL_COLLATION), unique=False)

    def __init__(self, sample_id, group_type, group_name):
        self.sample_id = sample_id
        self.group_type = group_type
        self.group_name = group_name

    def __repr__(self):
        return f"{self.id}. Sample {self.sample_id}: {self.group_type}:{self.group_name}"
