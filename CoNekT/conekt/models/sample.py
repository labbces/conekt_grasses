from conekt import db

SQL_COLLATION = 'NOCASE' if db.engine.name == 'sqlite' else ''

#Verify how to implement whooshee in the sample.
#@whooshee.register_model('description')

class Sample(db.Model):
    __tablename__ = 'samples'
    id = db.Column(db.Integer, primary_key=True)
    sample_name = db.Column(db.String(50, collation=SQL_COLLATION), unique=True)
    strandness = db.Column(db.Enum('unstranded', 'strand specific', name='RNA-Seq layout'), default='unstranded')
    layout = db.Column(db.Enum('paired-end', 'single-end', name='RNA-Seq layout'), default='single-end')
    description = db.Column(db.Text)
    replicate = db.Column(db.Integer, default=1)
    species_id = db.Column(db.Integer, db.ForeignKey('species.id', ondelete='CASCADE'), index=True)
    
    def __init__(self, sample_name, strandness, layout, species_id,
                 description, replicate):
        self.sample_name = sample_name
        self.strandness = strandness
        self.layout = layout
        self.description = description
        self.replicate = replicate
        self.species_id = species_id
    
    def __repr__(self):
        return str(self.id) + ". " + self.sample_name (self.species_id)
