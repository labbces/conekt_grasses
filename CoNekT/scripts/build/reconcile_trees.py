#!/usr/bin/env python3

import argparse

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, update

import newick
import json

import utils_scripts.phylo as phylo

parser = argparse.ArgumentParser(description='Reconcile trees in the database')
parser.add_argument('--tree_method_id', type=str, metavar='1',
                    dest='tree_method_id',
                    help='The internal identifier of tree method',
                    required=True)
parser.add_argument('--db_admin', type=str, metavar='DB admin',
                    dest='db_admin',
                    help='The database admin user',
                    required=True)
parser.add_argument('--db_name', type=str, metavar='DB name',
                    dest='db_name',
                    help='The database name',
                    required=True)
parser.add_argument('--db_password', type=str, metavar='DB password',
                    dest='db_password',
                    help='The database password',
                    required=False)

args = parser.parse_args()

if args.db_password:
    db_password = args.db_password
else:
    db_password = input("Enter the database password: ")


def reconcile_trees(tree_method_id, engine):

    with engine.connect() as conn:
        stmt = select(Sequence).where(Sequence.__table__.c.type == 'protein_coding')
        sequences = conn.execute(stmt).all()
    
    with engine.connect() as conn:
        stmt = select(Clade)
        clades = conn.execute(stmt).all()

    with engine.connect() as conn:
        stmt = select(Tree).where(Tree.__table__.c.method_id == tree_method_id)
        trees = conn.execute(stmt).all()

    seq_to_species = {s.name: s.species.code for s in sequences}
    seq_to_id = {s.name: s.id for s in sequences}
    clade_to_species = {c.name: json.loads(c.species) for c in clades}
    clade_to_id = {c.name: c.id for c in clades}

    new_associations = []

    phyloxml_data = {}

    for t in trees:
        # Load tree from Newick string and start reconciliating
        tree = newick.loads(t.data_newick)[0]

        for node in tree.walk():
            if len(node.descendants) != 2:
                if not node.is_binary:
                    # Print warning in case there is a non-binary node
                    print("[%d, %s] Skipping node... Can only reconcile binary nodes ..." % (tree.id, tree.label))
                # Otherwise it is a leaf node and can be skipped
                continue

            branch_one_seq = [l.name.strip() for l in node.descendants[0].get_leaves()]
            branch_two_seq = [l.name.strip() for l in node.descendants[1].get_leaves()]

            branch_one_species = set([seq_to_species[s] for s in branch_one_seq if s in seq_to_species.keys()])
            branch_two_species = set([seq_to_species[s] for s in branch_two_seq if s in seq_to_species.keys()])

            all_species = branch_one_species.union(branch_two_species)

            clade, _ = phylo.get_clade(all_species, clade_to_species)
            duplication = phylo.is_duplication(branch_one_species, branch_two_species, clade_to_species)

            duplication_consistency = None
            if duplication:
                duplication_consistency = phylo.duplication_consistency(branch_one_species, branch_two_species)

            tags = [clade_to_id[clade] if clade is not None else 0,
                    'D' if duplication else 'S',
                    duplication_consistency if duplication else 0]

            node.name = '_'.join([str(t) for t in tags])

            if clade is not None:
                for seq_one in branch_one_seq:
                    for seq_two in branch_two_seq:
                        new_association1 = {
                            'sequence_one_id': seq_to_id[seq_one],
                            'sequence_two_id': seq_to_id[seq_two],
                            'tree_id': t.id,
                            'clade_id': clade_to_id[clade],
                            'duplication': 1 if duplication else 0,
                            'duplication_consistency_score': duplication_consistency
                        }
                        new_associations.append(new_association1)
                        new_association_obj1 = SequenceSequenceCladeAssociation(**new_association1)
                        session.add(new_association_obj1)

                        new_association2 = {
                            'sequence_one_id': seq_to_id[seq_two],
                            'sequence_two_id': seq_to_id[seq_one],
                            'tree_id': t.id,
                            'clade_id': clade_to_id[clade],
                            'duplication': 1 if duplication else 0,
                            'duplication_consistency_score': duplication_consistency
                        }
                        new_associations.append(new_association2)
                        new_association_obj2 = SequenceSequenceCladeAssociation(**new_association2)
                        session.add(new_association_obj2)

        if len(new_associations) > 400:
            session.commit()
            new_associations = []

        # add newick tree to memory
        phyloxml_data[t.id] = newick.dumps([tree])

    session.commit()

    # Update PhyloXML data file for all trees
    for t in trees:
        if t.id in phyloxml_data.keys():
            with engine.connect() as conn:
                stmt = update(Tree).where(Tree.__table__.c.id == t.id).values(data_phyloxml=phyloxml_data[t.id])
                conn.execute(stmt)
                conn.commit()

db_admin = args.db_admin
db_name = args.db_name
tree_method_id = args.tree_method_id

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

Base.prepare(engine, reflect=True)

Sequence = Base.classes.sequences
Clade = Base.classes.clades
Tree = Base.classes.trees
TreeMethod = Base.classes.tree_methods
SequenceSequenceCladeAssociation = Base.classes.sequence_sequence_clade

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

reconcile_trees(tree_method_id, engine)

session.close()