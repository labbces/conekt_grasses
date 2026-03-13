#!/usr/bin/env python3

import argparse
import tarfile
import newick
from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

def read_sequence_ids(lines):
    output = {}
    for line in lines:
        line = line.strip()
        if line and ': ' in line:
            k, v = line.split(': ', 1)
            output[k] = v
    return output

def replace_ids(tree_string, conversion_table):
    tree = newick.loads(tree_string.strip(), strip_comments=True)[0]
    tree.remove_internal_names()
    for leaf in tree.get_leaves():
        if leaf.name in conversion_table:
            leaf.name = conversion_table[leaf.name]
    return newick.dumps([tree])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_gzip_trees', required=True)
    parser.add_argument('--gene_family_method_id', type=int, required=True)
    parser.add_argument('--gene_tree_method_description', required=True)
    parser.add_argument('--sequence_ids_orthofinder', required=True)
    parser.add_argument('--db_admin', required=True)
    parser.add_argument('--db_name', required=True)
    parser.add_argument('--db_password')
    args = parser.parse_args()

    pwd = args.db_password or input("Enter DB password: ")
    engine = create_engine(f"mysql+pymysql://{args.db_admin}:{pwd}@localhost/{args.db_name}")
    Base = automap_base()
    Base.prepare(autoload_with=engine)

    TreeMethod = Base.classes.tree_methods
    GeneFamily = Base.classes.gene_families
    Tree = Base.classes.trees

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Add method
        method = TreeMethod(
            gene_family_method_id=args.gene_family_method_id,
            description=args.gene_tree_method_description
        )
        session.add(method)
        session.commit()
        session.refresh(method)

        # Load sequence ID mapping
        with open(args.sequence_ids_orthofinder) as f:
            id_conversion = read_sequence_ids(f.readlines())

        # Load gene families for this method
        families = session.execute(
            select(GeneFamily).where(GeneFamily.method_id == args.gene_family_method_id)
        ).scalars().all()
        ori_name_to_id = {gf.original_name: gf.id for gf in families}

        print(f"Loaded {len(ori_name_to_id)} gene families.")

        trees_added = 0
        batch = []

        with tarfile.open(args.input_gzip_trees, 'r:gz') as tf:
            for member in tf:
                if not member.isfile():
                    continue
                name = member.name
                if name.startswith('./'):
                    name = name[2:]
                original_name = name.split('_')[0]

                gf_id = ori_name_to_id.get(original_name)
                if gf_id is None:
                    print(f"Warning: Family {original_name} not found.")
                    continue

                tree_data = tf.extractfile(member).read().decode('utf-8').replace('\r', '').replace('\n', '')
                newick_str = replace_ids(tree_data, id_conversion)

                tree = Tree(
                    gf_id=gf_id,
                    label=f"{original_name}_tree",
                    method_id=method.id,
                    data_newick=newick_str,
                    data_phyloxml=None
                )
                batch.append(tree)
                trees_added += 1

                if len(batch) >= 400:
                    session.add_all(batch)
                    session.commit()
                    batch.clear()
                    print(f"Committed {trees_added} trees...")

            if batch:
                session.add_all(batch)
                session.commit()

        print(f"✅ Successfully added {trees_added} gene trees.")
    finally:
        session.close()

if __name__ == '__main__':
    main()
