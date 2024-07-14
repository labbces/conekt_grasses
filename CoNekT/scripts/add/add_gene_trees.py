#!/usr/bin/env python3

import argparse

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

import tarfile
import newick


parser = argparse.ArgumentParser(description='Add gene trees to the database')
parser.add_argument('--input_gzip_trees', type=str, metavar='gene_trees.gz',
                    dest='trees_file',
                    help='The GZIP file with the gene trees',
                    required=True)
parser.add_argument('--gene_family_method_id', type=int, metavar='1',
                    dest='gene_family_method_id',
                    help='Gene family method identifier',
                    required=True)
parser.add_argument('--gene_family_method_description', type=str, metavar='Description of the gene family method',
                    dest='tree_method_description',
                    help='Gene tree method description',
                    required=True)
parser.add_argument('--sequence_ids_orthofinder', type=str, metavar='SequenceIDs.txt',
                    dest='sequenceids_file',
                    help='SequenceIDs.txt file from OrthoFinder',
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


def __read_sequence_ids(data):
    """
    Reads SequenceIDs.txt (file included in OrthoFinder Output) and parses it to a dict

    :param data: list of lines in SequenceIDs.txt
    :return: dict with key: OrthoFinder ID en value: the proper name
    """
    output = {}

    for l in data:
        if l.strip() != '':
            k, v = l.split(': ')
            output[k] = v

    return output


def __replace_ids(tree_string, conversion_table):
    """
    Replaces identifiers in a newick string with those defined in the conversion table

    :param tree_string: tree in newick format
    :param conversion_table: dict with name conversion
    :return: parsed tree, in newick format
    """
    tree = newick.loads(tree_string.strip(), strip_comments=True)[0]

    # Remove internal names, and need to be replaced with proper reconciliation.
    tree.remove_internal_names()

    for leaf in tree.get_leaves():
        if leaf.name in conversion_table.keys():
            leaf.name = conversion_table[leaf.name]

    return newick.dumps([tree])


def add_trees(gene_family_method_id, tree_method_description, tree_data_gzip, sequenceids_file, engine):
    
    # First Add Method
    new_method = TreeMethod()

    new_method.gene_family_method_id = gene_family_method_id
    new_method.description = tree_method_description

    session.add(new_method)
    session.commit()

    # Build conversion table from SequenceIDs.txt
    seqids_f = open(sequenceids_file, "r")
    id_conversion = __read_sequence_ids(seqids_f.readlines())

    # Get original gene family names (used to link trees to families)
    with engine.connect() as conn:
        stmt = select(GeneFamily).where(GeneFamily.__table__.c.method_id == new_method.gene_family_method_id)
        gfs = conn.execute(stmt).all()
    ori_name_to_id = {gf.original_name: gf.id for gf in gfs}
    tree_data = tree_data_gzip

    new_trees = []
    with tarfile.open(tree_data, mode='r:gz') as tf:
        for name, entry in zip(tf.getnames(), tf):
            tree_string = str(tf.extractfile(entry).read().decode('utf-8')).replace('\r', '').replace('\n','')

            # get the gene families original name from the filename
            if name.startswith('./'):
                # remove the ./ from the beginning of the name
                # this was an issue after compressing the trees with 
                # find . -name "OG*.txt" -print | tar -czvf trees.tgz -T -
                name_replaced = str(name.replace('./', ''))
                original_name = str(name_replaced.split('_')[0])
            else:
                original_name = str(name.split('_')[0])
                
            gf_id = None

            if original_name in ori_name_to_id.keys():
                gf_id = ori_name_to_id[original_name]
            else:
                print('%s: Family %s not found in gene families generated using method %d !' %
                        (name, original_name, new_method.gene_family_method_id))

            new_tree = {
                "gf_id": gf_id,
                "label": original_name + "_tree",
                "method_id": new_method.id,
                "data_newick": __replace_ids(tree_string, id_conversion),
                "data_phyloxml": None
            }

            new_trees.append(new_tree)
            new_tree_obj = Tree(**new_tree)
            session.add(new_tree_obj)

            # add 400 trees at the time, more can cause problems with some database engines
            if len(new_trees) > 400:
                session.commit()
                new_trees = []

        # add the last set of trees
        session.commit()


db_admin = args.db_admin
db_name = args.db_name
gene_family_method_id = args.gene_family_method_id
gene_tree_method_desc = args.tree_method_description
sequenceids_file = args.sequenceids_file
tree_data_gzip = args.trees_file

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

Base.prepare(engine, reflect=True)

TreeMethod = Base.classes.tree_methods
GeneFamily = Base.classes.gene_families
Tree = Base.classes.trees

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

add_trees(gene_family_method_id, gene_tree_method_desc, tree_data_gzip, sequenceids_file, engine)

session.close()