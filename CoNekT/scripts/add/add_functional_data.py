#!/usr/bin/env python3

import argparse
import xml.etree.ElementTree as ET
from copy import deepcopy
import gzip
from sqlalchemy import create_engine, select, delete
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

class OboEntry:
    def __init__(self):
        self.id = ''
        self.name = ''
        self.namespace = ''
        self.definition = ''
        self.is_a = []
        self.synonym = []
        self.alt_id = []
        self.extended_go = []
        self.is_obsolete = False

    def process(self, key, value):
        if key == "id":
            self.id = value
        elif key == "name":
            self.name = value
        elif key == "namespace":
            self.namespace = value
        elif key == "def":
            self.definition = value
        elif key == "is_a":
            parts = value.split()
            self.is_a.append(parts[0])
        elif key == "synonym":
            self.synonym.append(value)
        elif key == "alt_id":
            self.alt_id.append(value)
        elif key == "is_obsolete" and value == "true":
            self.is_obsolete = True

class OBOParser:
    def __init__(self):
        self.terms = []

    def readfile(self, filename, compressed=False):
        self.terms = []
        opener = gzip.open if compressed else open
        mode = 'rt' if compressed else 'r'
        with opener(filename, mode) as f:
            current_term = None
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line == "[Term]":
                    if current_term:
                        self.terms.append(current_term)
                    current_term = OboEntry()
                elif line == "[Typedef]":
                    if current_term:
                        self.terms.append(current_term)
                    current_term = None
                else:
                    if current_term is None:
                        continue
                    key, _, val = line.partition(":")
                    current_term.process(key.strip(), val.strip())
            if current_term:
                self.terms.append(current_term)

    def extend_go(self):
        hashed = {t.id: t for t in self.terms}
        for term in self.terms:
            extended = deepcopy(term.is_a)
            found_new = True
            while found_new:
                found_new = False
                for parent in extended[:]:
                    if parent in hashed:
                        for grand in hashed[parent].is_a:
                            if grand not in extended:
                                extended.append(grand)
                                found_new = True
            term.extended_go = extended

class InterProParser:
    def __init__(self):
        self.domains = []

    def readfile(self, filename):
        root = ET.parse(filename).getroot()
        for domain in root.findall('interpro'):
            self.domains.append({
                'label': domain.get('id'),
                'description': domain.get('short_name')
            })

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interpro_xml')
    parser.add_argument('--gene_ontology_obo')
    parser.add_argument('--cazyme')
    parser.add_argument('--db_admin', required=True)
    parser.add_argument('--db_name', required=True)
    parser.add_argument('--db_password')
    args = parser.parse_args()

    if not any([args.interpro_xml, args.gene_ontology_obo, args.cazyme]):
        raise ValueError("At least one functional data type must be provided.")

    pwd = args.db_password or input("Enter DB password: ")
    engine = create_engine(f"mysql+pymysql://{args.db_admin}:{pwd}@localhost/{args.db_name}")
    Base = automap_base()
    Base.prepare(autoload_with=engine)

    Interpro = Base.classes.interpro
    GO = Base.classes.go
    CAZYme = Base.classes.cazyme

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # InterPro
        if args.interpro_xml:
            session.execute(delete(Interpro))
            parser = InterProParser()
            parser.readfile(args.interpro_xml)
            batch = []
            for i, d in enumerate(parser.domains):
                batch.append(Interpro(**d))
                if len(batch) >= 40:
                    session.add_all(batch)
                    session.commit()
                    batch.clear()
            if batch:
                session.add_all(batch)
                session.commit()
            print(f"✅ Loaded {len(parser.domains)} InterPro domains.")

        # GO
        if args.gene_ontology_obo:
            session.execute(delete(GO))
            obo = OBOParser()
            compressed = args.gene_ontology_obo.endswith('.gz')
            obo.readfile(args.gene_ontology_obo, compressed=compressed)
            obo.extend_go()
            batch = []
            for i, term in enumerate(obo.terms):
                go = GO(
                    label=term.id,
                    name=term.name,
                    description=term.definition,
                    type=term.namespace,
                    obsolete=term.is_obsolete,
                    is_a=";".join(term.is_a),
                    extended_go=";".join(term.extended_go)
                )
                batch.append(go)
                if len(batch) >= 40:
                    session.add_all(batch)
                    session.commit()
                    batch.clear()
            if batch:
                session.add_all(batch)
                session.commit()
            print(f"✅ Loaded {len(obo.terms)} GO terms.")

        # CAZy
        if args.cazyme:
            session.execute(delete(CAZYme))
            class_dict = {
                'GH': 'Glycoside Hydrolase',
                'GT': 'GlycosylTransferase',
                'PL': 'Polysaccharide Lyase',
                'CE': 'Carbohydrate Esterase',
                'AA': 'Auxiliary Activities',
                'CBM': 'Carbohydrate-Binding Module'
            }
            batch = []
            with open(args.cazyme) as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) == 2:
                        family, activities = parts
                        prefix = ''.join(c for c in family if c.isalpha())
                        cazyme_class = class_dict.get(prefix, '')
                        batch.append(CAZYme(
                            family=family,
                            cazyme_class=cazyme_class,
                            activities=activities
                        ))
                        if len(batch) >= 40:
                            session.add_all(batch)
                            session.commit()
                            batch.clear()
            if batch:
                session.add_all(batch)
                session.commit()
            print(f"✅ Loaded CAZy families from {args.cazyme}.")

    finally:
        session.close()

if __name__ == '__main__':
    main()
