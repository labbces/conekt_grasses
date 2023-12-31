#!/usr/bin/env python3

import argparse
import json

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

from crossref.restful import Works

# Create arguments
parser = argparse.ArgumentParser(description='Add expression data to the database')
parser.add_argument('--expression_matrix', type=str, metavar='matrix.txt',
                    dest='expression_file',
                    help='The expression_matrix.txt file from LSTrAP',
                    required=True)
parser.add_argument('--species_code', type=str, metavar='Svi',
                    dest='species_code',
                    help='The CoNekT Grasses species code',
                    required=True)
parser.add_argument('--sample_annotation', type=str, metavar='Sample Annotation File',
                    dest='sample_annotation',
                    help='Sample annotation file',
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


def add_literature(doi, engine):

        works = Works()
        # verify if DOI already exists in DB, if not, collect data
        literature_info = works.doi(doi)

        qtd_author = len(literature_info['author'])
        
        if 'family' in literature_info['author'][0].keys():
            author_names = literature_info['author'][0]['family']
        else:
            author_names = literature_info['author'][0]['name']

        title = literature_info['title']
        
        if 'published-print' in literature_info.keys():
            public_year = literature_info['published-print']['date-parts'][0][0]
        elif 'published-online' in literature_info.keys():
            public_year = literature_info['published-online']['date-parts'][0][0]
        else:
            public_year = literature_info['issued']['date-parts'][0][0]

        new_literature = LiteratureItem(qtd_author=qtd_author,
                                        author_names=author_names,
                                        title=title,
                                        public_year=public_year,
                                        doi=doi)
    
        with engine.connect() as conn:
            stmt = select(LiteratureItem).where(LiteratureItem.__table__.c.doi == doi)
            literature = conn.execute(stmt).first()

        # literature is not in the DB yet, add it
        if not literature:
            session.add(new_literature)
            session.commit()

            return new_literature
        else:
            return literature

def add_sample_po_association(sample_name, po_term, po_branch):

    with engine.connect() as conn:
        stmt = select(Sample).where(Sample.__table__.c.sample_name == sample_name)
        sample = conn.execute(stmt).first()
    
    if not sample:
        print(f'Sample not found in database: {sample_name}')
        exit(1)
    
    with engine.connect() as conn:
        stmt = select(PlantOntology).where(PlantOntology.__table__.c.po_term == po_term)
        po = conn.execute(stmt).first()
    
    if not po:
        print(f'PO not found in database: {po.po_term}')
        exit(1)

    species_id = sample.species_id

    with engine.connect() as conn:
        stmt = select(SamplePOAssociation)\
        .where(SamplePOAssociation.__table__.c.sample_id == sample.id,
               SamplePOAssociation.__table__.c.po_id == po.id)
        sample_po = conn.execute(stmt).first()
    
    if sample_po:
        print(f'Association between sample {sample.sample_name} and PO {po.po_class} already exists.')
        exit(1)
    else:
        association = SamplePOAssociation(**{'sample_id': sample.id,
                    'po_id': po.id,
                    'species_id': species_id,
                    'po_branch': po_branch})
    
        session.add(association)
        session.commit()

def add_sample_peco_association(sample_name, peco_term):

    # Not checking sample existence
    # because it is already done in add_sample_po_association
    # for which PO anatomy is mandatory

    with engine.connect() as conn:
        stmt = select(Sample).where(Sample.__table__.c.sample_name == sample_name)
        sample = conn.execute(stmt).first()

    with engine.connect() as conn:
        stmt = select(PlantExperimentalConditionsOntology)\
        .where(PlantExperimentalConditionsOntology.__table__.c.peco_term == peco_term)
        peco = conn.execute(stmt).first()
    
    if not peco:
        print(f'PECO not found in database: {peco.peco_term}')
        exit(1)

    species_id = sample.species_id

    with engine.connect() as conn:
        stmt = select(SamplePECOAssociation)\
        .where(SamplePECOAssociation.__table__.c.sample_id == sample.id,
               SamplePECOAssociation.__table__.c.peco_id == peco.id)
        sample_peco = conn.execute(stmt).first()
    
    if sample_peco:
        print(f'Association between sample {sample.sample_name} and PECO {peco.peco_class} already exists.')
        exit(1)
    else:
        association = SamplePECOAssociation(**{'sample_id': sample.id,
                    'peco_id': peco.id,
                    'species_id': species_id})
    
        session.add(association)
        session.commit()

def add_sample_lit_association(sample_name, lit_doi, engine):
        
    # Not checking sample existence
    # because it is already done in add_sample_po_association
    # for which PO anatomy is mandatory

    with engine.connect() as conn:
        stmt = select(Sample).where(Sample.__table__.c.sample_name == sample_name)
        sample = conn.execute(stmt).first()

    with engine.connect() as conn:
        stmt = select(LiteratureItem).where(LiteratureItem.__table__.c.doi == lit_doi)
        literature_item = conn.execute(stmt).first()

    if not literature_item:
        literature_item = add_literature(lit_doi, engine)
        
    association = {'sample_id': sample.id,
                   'literature_id': literature_item.id}
    
    session.add(SampleLitAssociation(**association))
    session.commit()


def add_profile_from_lstrap(matrix_file, annotation_file, species_code, engine, order_color_file=None):
    """
    Function to convert an (normalized) expression matrix (lstrap output) into a profile

    :param matrix_file: path to the expression matrix
    :param annotation_file: path to the file assigning samples to conditions
    :param species_id: internal id of the species
    :param order_color_file: tab delimited file that contains the order and color of conditions
    """

    with engine.connect() as conn:
        stmt = select(Species).where(Species.__table__.c.code == species_code)
        species_id = conn.execute(stmt).first().id
    
    if not species_id:
        print(f'Species not found in database: {species_code}')
        exit(1)

    annotation = {}

    with open(annotation_file, 'r') as fin:
        # get rid of the header
        _ = fin.readline()
        for line in fin:
            # 8 parts (columns)
            parts = line.split('\t')
            if len(parts) == 8:        
                run, literature_doi,\
                description, strandness,\
                layout, po_anatomy,\
                po_dev_stage, peco = parts
                peco = peco.rstrip()
                
                session.add(Sample(sample_name=run,
                           strandness=strandness,
                           layout=layout,
                           description=description,
                           species_id=species_id))
                session.commit()

                annotation[run] = {}
                annotation[run]["description"] = description

                # 'po_anatomy' is mandatory
                if po_anatomy:
                    annotation[run]["po_anatomy"] = po_anatomy
                    add_sample_po_association(run, po_anatomy, "po_anatomy")
                    with engine.connect() as conn:
                        stmt = select(PlantOntology).where(PlantOntology.__table__.c.po_term == po_anatomy)
                        po = conn.execute(stmt).first()
                    annotation[run]["po_anatomy_class"] = po.po_class
                else:
                    print(f"The 'po_anatomy' of sample {run} is absent (mandatory info)")
                    exit(1)
                # 'po_dev_stage' is optional
                if po_dev_stage:
                    annotation[run]["po_dev_stage"] = po_dev_stage
                    add_sample_po_association(run, po_dev_stage, "po_dev_stage")
                    with engine.connect() as conn:
                        stmt = select(PlantOntology).where(PlantOntology.__table__.c.po_term == po_dev_stage)
                        po = conn.execute(stmt).first()
                    annotation[run]["po_dev_stage_class"] = po.po_class
                # 'peco' is optional
                if peco:
                    annotation[run]["peco"] = peco
                    add_sample_peco_association(run, peco)
                    with engine.connect() as conn:
                        stmt = select(PlantExperimentalConditionsOntology).where(PlantExperimentalConditionsOntology.__table__.c.peco_term == peco)
                        peco_details = conn.execute(stmt).first()
                    annotation[run]["peco_class"] = peco_details.peco_class
            else:
                print(f"Error parsing line: {line}")
                exit(1)
                
            # Add literature-sample association
            add_sample_lit_association(run, literature_doi, engine)

    #See the modifications in other parts of code
    order, colors = [], []
    if order_color_file is not None:
        with open(order_color_file, 'r') as fin:
            for line in fin:
                try:
                    o, c = line.strip().split('\t')
                    order.append(o)
                    colors.append(c)
                except Exception as _:
                    pass
    
    # build conversion table for sequences
    with engine.connect() as conn:
        stmt = select(Sequence).where(Sequence.__table__.c.species_id == species_id,
                                      Sequence.__table__.c.type == "protein_coding")
        sequences = conn.execute(stmt).all()

    sequence_dict = {}  # key = sequence name uppercase, value internal id
    for s in sequences:
        sequence_dict[s.name.upper()] = s.id

    with open(matrix_file) as fin:
        # read header
        _, *colnames = fin.readline().rstrip().split()

        colnames = [c.replace('.htseq', '') for c in colnames]

        # determine order after annotation is not defined
        if order == []:        
            for c in colnames:
                if c in annotation.keys():
                    if annotation[c]['po_anatomy_class'] not in order:
                        order.append(annotation[c]['po_anatomy_class'])
            order.sort()

        # read each line and build profile
        new_probes = []
        for line in fin:
            transcript, *values = line.rstrip().split()
            profile = {'TPM': {},
                        'annotation': {},
                        'PO_anatomy': {},
                        'PO_anatomy_class': {},
                        'PO_dev_stage': {},
                        'PO_dev_stage_class': {},
                        'PECO': {},
                        'PECO_class': {},}

            for c, v in zip(colnames, values):
                if c in annotation.keys():
                    profile['TPM'][c] = float(v)
                    profile['annotation'][c] = annotation[c]['description']
                    profile['PO_anatomy'][c] = annotation[c]["po_anatomy"]
                    profile['PO_anatomy_class'][c] = annotation[c]["po_anatomy_class"]
                    # not mandatory fields
                    if 'po_dev_stage' in annotation[c]:
                        profile['PO_dev_stage'][c] = annotation[c]["po_dev_stage"]
                        profile['PO_dev_stage_class'][c] = annotation[c]["po_dev_stage_class"]
                    if 'peco' in annotation[c]:
                        profile['PECO'][c] = annotation[c]["peco"]
                        profile['PECO_class'][c] = annotation[c]["peco_class"]


            new_probe = {"species_id": species_id,
                            "probe": transcript,
                            "sequence_id": sequence_dict[transcript.upper()] if transcript.upper() in sequence_dict.keys() else None,
                            "profile": json.dumps({"order": order,
                                                    "colors": colors,
                                                    "data": profile})
                            }

            new_probes.append(new_probe)
            session.add(ExpressionProfile(**new_probe))

            if len(new_probes) > 400:
                session.commit()
                new_probes = []

        session.commit()

db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

Base.prepare(engine, reflect=True)

Species = Base.classes.species
Sequence = Base.classes.sequences
Sample = Base.classes.samples
SampleLitAssociation = Base.classes.sample_literature
PlantOntology = Base.classes.plant_ontology
PlantExperimentalConditionsOntology = Base.classes.plant_experimental_conditions_ontology
ExpressionProfile = Base.classes.expression_profiles
SamplePOAssociation = Base.classes.sample_po
SamplePECOAssociation = Base.classes.sample_peco
LiteratureItem = Base.classes.literature

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

species_code = args.species_code
matrix_file = args.expression_file
annotation_file = args.sample_annotation

# Adds expression profiles from LSTrAP
add_profile_from_lstrap(matrix_file, annotation_file, species_code, engine)

session.close()