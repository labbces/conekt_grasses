from conekt import db, whooshee
from conekt.models.relationships import sequence_interpro
from conekt.models.relationships.sequence_interpro import SequenceInterproAssociation

from sqlalchemy.orm import joinedload


SQL_COLLATION = None


@whooshee.register_model('description')
class Interpro(db.Model):
    __tablename__ = 'interpro'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50, collation=SQL_COLLATION), unique=True, index=True)
    description = db.Column(db.Text)

    clade_id = db.Column(db.Integer, db.ForeignKey('clades.id', ondelete='SET NULL'), index=True)

    sequences = db.relationship('Sequence', secondary=sequence_interpro, lazy='dynamic')

    # Other properties
    # sequence_associations = defined in SequenceInterproRelationship

    def __init__(self, label, description):
        self.label = label
        self.description = description

    @property
    def species_codes(self):
        """
        Finds all species the family has genes from
        :return: a list of all species (codes)
        """

        sequences = self.sequences.options(joinedload('species')).all()

        output = []

        for s in sequences:
            if s.species.code not in output:
                output.append(s.species.code)

        return output

    @property
    def species_counts(self):
        """
        Generates a phylogenetic profile of a gene family
        :return: a dict with counts per species (codes are keys)
        """

        sequences = self.sequences.options(joinedload('species')).all()

        output = {}

        for s in sequences:
            if s.species.code not in output:
                output[s.species.code] = 1
            else:
                output[s.species.code] += 1

        return output

    @staticmethod
    def sequence_stats(sequence_ids):
        """
        Takes a list of sequence IDs and returns InterPro stats for those sequences

        :param sequence_ids: list of sequence ids
        :return: dict with for each InterPro domain linked with any of the input sequences stats
        """
        data = SequenceInterproAssociation.query.filter(SequenceInterproAssociation.sequence_id.in_(sequence_ids)).all()

        return Interpro.__sequence_stats_associations(data)

    @staticmethod
    def sequence_stats_subquery(sequences):
        subquery = sequences.subquery()
        data = SequenceInterproAssociation.query.join(subquery, SequenceInterproAssociation.sequence_id == subquery.c.id).all()

        return Interpro.__sequence_stats_associations(data)

    @staticmethod
    def __sequence_stats_associations(associations):
        output = {}

        for d in associations:
            if d.interpro_id not in output.keys():
                output[d.interpro_id] = {
                    'domain': d.domain,
                    'count': 1,
                    'sequences': [d.sequence_id],
                    'species': [d.sequence.species_id]
                }
            else:
                output[d.interpro_id]['count'] += 1
                if d.sequence_id not in output[d.interpro_id]['sequences']:
                    output[d.interpro_id]['sequences'].append(d.sequence_id)
                if d.sequence.species_id not in output[d.interpro_id]['species']:
                    output[d.interpro_id]['species'].append(d.sequence.species_id)

        for k, v in output.items():
            v['species_count'] = len(v['species'])
            v['sequence_count'] = len(v['sequences'])

        return output

    @property
    def interpro_stats(self):
        return Interpro.sequence_stats_subquery(self.sequences)

    @property
    def go_stats(self):
        from conekt.models.go import GO

        return GO.sequence_stats_subquery(self.sequences)

    @property
    def family_stats(self):
        from conekt.models.gene_families import GeneFamily

        return GeneFamily.sequence_stats_subquery(self.sequences)
