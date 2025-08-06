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
        data = SequenceTFAssociation.query.join(subquery, SequenceTFAssociation.sequence_id == subquery.c.id).all()

        return TranscriptionRegulator.__sequence_stats_associations(data)

    @property
    def tf_stats(self):
        return TranscriptionRegulator.sequence_stats_subquery(self.sequences)

    @property
    def family_stats(self):
        from conekt.models.gene_families import GeneFamily
        return GeneFamily.sequence_stats_subquery(self.sequences)

    @staticmethod
    def add_tf_from_tab(filename, species_id):
        gene_hash = {}
        tf_hash = {}

        all_sequences = Sequence.query.filter(Sequence.species_id == species_id, Sequence.type == 'protein_coding').all()
        all_tfs = TranscriptionRegulator.query.all()

        for sequence in all_sequences:
            gene_hash[sequence.name] = sequence

        for tf in all_tfs:
            tf_hash[tf.family] = tf

        associations = []
        gene_tf = defaultdict(list)
        
        with open(filename, "r") as f:
            header = f.readline()  # skip header
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 5:
                    continue
                gene, family, type, query_start, query_end = parts[0], parts[1], parts[2], parts[3], parts[4]
                if gene in gene_hash.keys():
                    current_sequence = gene_hash[gene]
                    if family in tf_hash.keys():
                        current_tf = tf_hash[family]
                        association = {
                            "sequence_id": current_sequence.id,
                            "tf_id": current_tf.id,
                            "query_start": int(query_start),
                            "query_end": int(query_end)
                        }
                        associations.append(association)
                        if family not in gene_tf[gene]:
                            gene_tf[gene].append(family)
                    else:
                        print(family, "not found in the database.")
                else:
                    print("Gene", gene, "not found in the database.")
                if len(associations) > 400:
                    db.engine.execute(SequenceTFAssociation.__table__.insert(), associations)
                    associations = []
        if associations:
            db.engine.execute(SequenceTFAssociation.__table__.insert(), associations)

    @staticmethod
    def add_from_txt(filename, empty=True):
        """
        Populates transcription_regulator table with families and descriptions from a TXT file
        :param filename: path to TXT file
        :param empty: If True the table will be cleared before uploading the new families, default = True
        """
        if empty:
            try:
                db.session.query(TranscriptionRegulator).delete()
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(e)
        with open(filename, 'r') as fin:
            i = 0
            for line in fin:
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    family, description = parts[0], parts[1]
                    tf = TranscriptionRegulator(family=family, type=None, description=description)
                    db.session.add(tf)
                    i += 1
                if i % 40 == 0:
                    try:
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        print(e)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)