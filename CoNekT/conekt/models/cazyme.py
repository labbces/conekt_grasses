from conekt import db, whooshee
from conekt.models.relationships import sequence_cazyme
from conekt.models.relationships.sequence_cazyme import SequenceCAZYmeAssociation

SQL_COLLATION = 'NOCASE' if db.engine.name == 'sqlite' else ''

@whooshee.register_model('family', 'cazyme_class', 'activities')
class CAZYme(db.Model):
    __tablename__ = 'cazyme'
    id = db.Column(db.Integer, primary_key=True)
    family = db.Column(db.Text)
    cazyme_class = db.Column(db.Text)
    activities = db.Column(db.Text)

    sequences = db.relationship('Sequence', secondary=sequence_cazyme, lazy='dynamic')

    def __init__(self, family, cazyme_class, activities):
        self.family = family
        self.cazyme_class = cazyme_class
        self.activities = activities

    def set_all(self, family, cazyme_class, activities):
        self.family = family
        self.cazyme_class = cazyme_class
        self.activities = activities


    @staticmethod
    def sequence_stats(sequence_ids, exclude_predicted=True):
        """
        Takes a list of sequence IDs and returns CAZYme stats for those sequences

        :param sequence_ids: list of sequence ids
        :param exclude_predicted: if True (default) predicted CAZYme labels will be excluded
        :return: dict with for each CAZYme linked with any of the input sequences stats
        """
        data = SequenceCAZYmeAssociation.query.filter(SequenceCAZYmeAssociation.sequence_id.in_(sequence_ids)).all()

        return CAZYme.__sequence_stats_associations(data)


    @staticmethod
    def __sequence_stats_associations(associations):
        output = {}
        for d in associations:
            if d.cazyme_id not in output.keys():
                output[d.cazyme_id] = {
                    'cazyme': d.cazyme,
                    'count': 1,
                    'sequences': [d.sequence_id],
                    'species': [d.sequence.species_id]
                }
            else:
                output[d.cazyme_id]['count'] += 1
                if d.sequence_id not in output[d.cazyme_id]['sequences']:
                    output[d.cazyme_id]['sequences'].append(d.sequence_id)
                if d.sequence.species_id not in output[d.cazyme_id]['species']:
                    output[d.cazyme_id]['species'].append(d.sequence.species_id)

        for k, v in output.items():
            v['species_count'] = len(v['species'])
            v['sequence_count'] = len(v['sequences'])

        return output


    @staticmethod
    def sequence_stats_subquery(sequences):
        subquery = sequences.subquery()
        data = SequenceCAZYmeAssociation.query.join(subquery, SequenceCAZYmeAssociation.sequence_id == subquery.c.id).all()

        return CAZYme.__sequence_stats_associations(data)

    
    @property
    def cazyme_stats(self):
        sequence_ids = [s.id for s in self.sequences.all()]

        return CAZYme.sequence_stats_subquery(self.sequences)

    @property
    def family_stats(self):
        from conekt.models.gene_families import GeneFamily

        return GeneFamily.sequence_stats_subquery(self.sequences)
