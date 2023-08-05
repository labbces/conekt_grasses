from conekt import db, whooshee
from conekt.models.relationships import sequence_cazyme
from conekt.models.relationships.sequence_cazyme import SequenceCAZYmeAssociation
from conekt.models.sequences import Sequence

from collections import defaultdict

import json

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
        query = SequenceCAZYmeAssociation.query.filter(SequenceCAZYmeAssociation.sequence_id.in_(sequence_ids))

        if exclude_predicted:
            query = query.filter(SequenceCAZYmeAssociation.predicted == 0)

        data = query.all()

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

    @staticmethod
    def add_cazyme_from_tab(filename, species_id):
        gene_hash = {}
        cazyme_hash = {}

        all_sequences = Sequence.query.filter(Sequence.species_id == species_id, Sequence.type == 'protein_coding').all()
        all_cazyme = CAZYme.query.all()

        for sequence in all_sequences:
            gene_hash[sequence.name] = sequence

        for term in all_cazyme:
            cazyme_hash[term.family] = term

        associations = []

        gene_cazyme = defaultdict(list)

        with open(filename, "r") as f:
            for line in f:
                term, hmm_length, gene, query_length, e_value, start, end = line.strip().split('\t')
                term = term.replace('.hmm', '')
                if gene in gene_hash.keys():
                    current_sequence = gene_hash[gene]
                    if term in cazyme_hash.keys():
                        current_term = cazyme_hash[term]
                        association = {
                            "sequence_id": current_sequence.id,
                            "cazyme_id": current_term.id,
                            "hmm_length": hmm_length,
                            "query_length": query_length,
                            "e_value": e_value,
                            "query_start": start,
                            "query_end": end,
                            }
                        associations.append(association)

                        if term not in gene_cazyme[gene]:
                            gene_cazyme[gene].append(term)

                    else:
                        print(term, "not found in the database.")
                else:
                    print("Gene", gene, "not found in the database.")

                if len(associations) > 400:
                    db.engine.execute(SequenceCAZYmeAssociation.__table__.insert(), associations)
                    associations = []

        db.engine.execute(SequenceCAZYmeAssociation.__table__.insert(), associations)


    @staticmethod
    def add_from_txt(filename, empty=True):
        """
        Populates interpro table with domains and descriptions from the official website's TXT file

        :param filename: path to TXT file
        :param empty: If True the interpro table will be cleared before uploading the new domains, default = True
        """
        # If required empty the table first
        if empty:
            try:
                db.session.query(CAZYme).delete()
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(e)
        
        class_dict = {
            'GH':'Glycoside Hydrolase',
            'GT':'GlycosylTransferase',
            'PL':'Polysaccharide Lyase',
            'CE':'Carbohydrate Esterase',
            'AA':'Auxiliary Activitie',
            'CBM':'Carbohydrate-Binding Module'
        }

        with open(filename, 'r') as fin:
            i = 0
            for line in fin:
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    family, cazyme_class, activities = parts[0], '', parts[1]
                    
                    string = ''
                    for char in parts[0]:
                        if char.isalpha():
                            string += char
                    cazyme_class = class_dict[string]

                    cazyme = CAZYme(family=family, cazyme_class=cazyme_class, activities=activities)
                    db.session.add(cazyme)
                    i += 1
                if i % 40 == 0:
                # commit to the db frequently to allow WHOOSHEE's indexing function to work without timing out
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