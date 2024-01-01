from conekt import db, whooshee
from conekt.models.relationships import sample_po
from conekt.models.relationships.sample_po import SamplePOAssociation

from sqlalchemy.orm import undefer
import operator
import sys

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

    # adding sample information in the DB
    @staticmethod
    def add(sample_name, strandness, layout, description, species_id, replicate=1):

        new_sample = Sample(sample_name, strandness=strandness, layout=layout,
                            description=description, replicate=replicate,
                            species_id=species_id)
        
        sample = Sample.query.filter_by(sample_name=sample_name).first()

        if sample is None:
            try:
                db.session.add(new_sample)
                db.session.commit()
            except:
                db.rollback()

            return new_sample.id
        else:
            return sample.id
