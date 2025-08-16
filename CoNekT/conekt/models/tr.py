from conekt import db, whooshee
from conekt.models.relationships import sequence_tr
from conekt.models.sequences import Sequence
from conekt.models.relationships.sequence_tr import SequenceTRAssociation
from collections import defaultdict
import json

@whooshee.register_model('family', 'type', 'description')
class TranscriptionRegulator(db.Model):
    __tablename__ = 'transcription_regulator'
    id = db.Column(db.Integer, primary_key=True)
    family = db.Column(db.Text)
    type = db.Column(db.Text) 
    description = db.Column(db.Text)  
    sequences = db.relationship('Sequence', secondary=sequence_tr, lazy='dynamic', back_populates='trs')

    def __init__(self, family, type, description=None):
        self.family = family
        self.type = type
        self.description = description

    def set_all(self, family, type, description=None):
        self.family = family
        self.type = type
        self.description = description

    @staticmethod
    def sequence_stats(sequence_ids):
        from conekt_grasses.CoNekT.conekt.models.relationships.sequence_tr import SequenceTRAssociation
        data = SequenceTRAssociation.query.filter(SequenceTRAssociation.sequence_id.in_(sequence_ids)).all()
        return TranscriptionRegulator.__sequence_stats_associations(data)

    @staticmethod
    def __sequence_stats_associations(associations):
        output = {}
        for d in associations:
            if d.tf_id not in output.keys():
                output[d.tf_id] = {
                    'tf': d.tf,
                    'count': 1,
                    'sequences': [d.sequence_id],
                    'species': [d.sequence.species_id]
                }
            else:
                output[d.tf_id]['count'] += 1
                if d.sequence_id not in output[d.tf_id]['sequences']:
                    output[d.tf_id]['sequences'].append(d.sequence_id)
                if d.sequence.species_id not in output[d.tf_id]['species']:
                    output[d.tf_id]['species'].append(d.sequence.species_id)
        for k, v in output.items():
            v['species_count'] = len(v['species'])
            v['sequence_count'] = len(v['sequences'])
        return output

    @staticmethod
    def sequence_stats_subquery(sequences):
        subquery = sequences.subquery()
        data = SequenceTRAssociation.query.join(subquery, SequenceTRAssociation.sequence_id == subquery.c.id).all()

        return TranscriptionRegulator.__sequence_stats_associations(data)

    @property
    def tf_stats(self):
        return TranscriptionRegulator.sequence_stats_subquery(self.sequences)

    @property
    def family_stats(self):
        from conekt.models.gene_families import GeneFamily
        return GeneFamily.sequence_stats_subquery(self.sequences)