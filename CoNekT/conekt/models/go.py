from conekt import db, whooshee
from conekt.models.relationships import sequence_go
from conekt.models.relationships.sequence_go import SequenceGOAssociation
from conekt.models.sequences import Sequence

import json

SQL_COLLATION = None


@whooshee.register_model('name', 'description')
class GO(db.Model):
    __tablename__ = 'go'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50, collation=SQL_COLLATION), unique=True, index=True)
    name = db.Column(db.Text)
    type = db.Column(db.Enum('biological_process', 'molecular_function', 'cellular_component', name='go_type'))
    description = db.Column(db.Text)
    obsolete = db.Column(db.SmallInteger)
    is_a = db.Column(db.Text)
    extended_go = db.Column(db.Text)
    species_counts = db.Column(db.Text)

    sequences = db.relationship('Sequence', secondary=sequence_go, lazy='dynamic')

    # Other properties
    #
    # sequence_associations declared in 'SequenceGOAssociation'
    # enriched_clusters declared in 'ClusterGOEnrichment'

    def __init__(self, label, name, go_type, description, obsolete, is_a, extended_go):
        self.label = label
        self.name = name
        self.type = go_type
        self.description = description
        self.obsolete = obsolete
        self.is_a = is_a
        self.extended_go = extended_go
        self.species_counts = ""

    def set_all(self, label, name, go_type, description, extended_go):
        self.label = label
        self.name = name
        self.type = go_type
        self.description = description
        self.extended_go = extended_go
        self.species_counts = ""

    @property
    def short_type(self):
        if self.type == 'biological_process':
            return 'BP'
        elif self.type == 'molecular_function':
            return 'MF'
        elif self.type == 'cellular_component':
            return 'CC'
        else:
            return 'UNK'

    @property
    def readable_type(self):
        if self.type == 'biological_process':
            return 'Biological process'
        elif self.type == 'molecular_function':
            return 'Molecular function'
        elif self.type == 'cellular_component':
            return 'Cellular component'
        else:
            return 'Unknown type'

    @property
    def parent_count(self):
        """
        Returns total number of genes 'above' this gene in the DAG
        :return:
        """
        return len(self.extended_go.split(';')) if self.extended_go != '' else 0

    @property
    def interpro_stats(self):
        from conekt.models.interpro import Interpro

        return Interpro.sequence_stats_subquery(self.sequences)

    @property
    def go_stats(self):
        return GO.sequence_stats_subquery(self.sequences)

    @property
    def family_stats(self):
        from conekt.models.gene_families import GeneFamily

        return GeneFamily.sequence_stats_subquery(self.sequences)

    @staticmethod
    def sequence_stats(sequence_ids, exclude_predicted=True):
        """
        Takes a list of sequence IDs and returns InterPro stats for those sequences

        :param sequence_ids: list of sequence ids
        :param exclude_predicted: if True (default) predicted GO labels will be excluded
        :return: dict with for each InterPro domain linked with any of the input sequences stats
        """
        query = SequenceGOAssociation.query.filter(SequenceGOAssociation.sequence_id.in_(sequence_ids))

        if exclude_predicted:
            query = query.filter(SequenceGOAssociation.predicted == 0)

        data = query.all()

        return GO.__sequence_stats_associations(data)

    @staticmethod
    def sequence_stats_subquery(sequences, exclude_predicted=True):
        subquery = sequences.subquery()

        query = SequenceGOAssociation.query

        if exclude_predicted:
            query = query.filter(SequenceGOAssociation.predicted == 0)

        data = query.join(subquery, SequenceGOAssociation.sequence_id == subquery.c.id).all()

        return GO.__sequence_stats_associations(data)

    @staticmethod
    def __sequence_stats_associations(associations):
        output = {}
        for d in associations:
            if d.go_id not in output.keys():
                output[d.go_id] = {
                    'go': d.go,
                    'count': 1,
                    'sequences': [d.sequence_id],
                    'species': [d.sequence.species_id]
                }
            else:
                output[d.go_id]['count'] += 1
                if d.sequence_id not in output[d.go_id]['sequences']:
                    output[d.go_id]['sequences'].append(d.sequence_id)
                if d.sequence.species_id not in output[d.go_id]['species']:
                    output[d.go_id]['species'].append(d.sequence.species_id)

        for k, v in output.items():
            v['species_count'] = len(v['species'])
            v['sequence_count'] = len(v['sequences'])

        return output

    @staticmethod
    def update_species_counts():
        """
        Adds phylo-profile to each go-label, results are stored in the database

        :param exclude_predicted: if True (default) predicted GO labels will be excluded
        """
        # link species to sequences
        sequences = db.engine.execute(db.select([Sequence.__table__.c.id, Sequence.__table__.c.species_id])).fetchall()

        sequence_to_species = {}
        for seq_id, species_id in sequences:
            if species_id is not None:
                sequence_to_species[seq_id] = int(species_id)

        # get go for all genes
        associations = db.engine.execute(
            db.select([SequenceGOAssociation.__table__.c.sequence_id,
                       SequenceGOAssociation.__table__.c.go_id], distinct=True)\
            .where(SequenceGOAssociation.__table__.c.predicted == 0))\
            .fetchall()

        count = {}
        for seq_id, go_id in associations:
            species_id = sequence_to_species[seq_id]

            if go_id not in count.keys():
                count[go_id] = {}

            if species_id not in count[go_id]:
                count[go_id][species_id] = 1
            else:
                count[go_id][species_id] += 1

        # update counts
        for go_id, data in count.items():
            db.engine.execute(db.update(GO.__table__)
                              .where(GO.__table__.c.id == go_id)
                              .values(species_counts=json.dumps(data)))
