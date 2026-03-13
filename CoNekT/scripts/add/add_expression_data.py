#!/usr/bin/env python3

import argparse
import json
import time
import unicodedata
from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from crossref.restful import Works

def clean_latin1(text):
    """Remove ou substitui caracteres não suportados em latin1"""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFD', str(text))
    ascii_only = normalized.encode('ascii', 'ignore').decode('ascii')
    cleaned = ''.join(c for c in ascii_only if ord(c) < 128)
    return cleaned.strip() or "Unknown"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expression_matrix', required=True)
    parser.add_argument('--sample_annotation', required=True)
    parser.add_argument('--species_code', required=True)
    parser.add_argument('--db_admin', required=True)
    parser.add_argument('--db_name', required=True)
    parser.add_argument('--db_password')
    args = parser.parse_args()

    pwd = args.db_password or input("Enter DB password: ")
    engine = create_engine(f"mysql+pymysql://{args.db_admin}:{pwd}@localhost/{args.db_name}")
    Base = automap_base()
    Base.prepare(autoload_with=engine)

    Species = Base.classes.species
    Sequence = Base.classes.sequences
    Sample = Base.classes.samples
    PlantOntology = Base.classes.plant_ontology
    PECO = Base.classes.plant_experimental_conditions_ontology
    Lit = Base.classes.literature
    SampleLit = Base.classes.sample_literature
    SamplePO = Base.classes.sample_po
    SamplePECO = Base.classes.sample_peco
    ExprProf = Base.classes.expression_profiles

    Session = sessionmaker(bind=engine)
    session = Session()

    def get_or_create_lit(doi):
        # Verifica se já existe
        existing = session.execute(select(Lit).where(Lit.doi == doi)).scalar_one_or_none()
        if existing:
            return existing

        try:
            works = Works()
            info = works.doi(doi)
            
            # Processa autor
            author_info = info['author'][0] if info.get('author') else {}
            author = author_info.get('family') or author_info.get('name', 'Unknown')
            author = clean_latin1(author)

            # Processa título
            title_raw = info.get('title', [''])[0] if isinstance(info.get('title'), list) else info.get('title', '')
            title = clean_latin1(title_raw)

            # Processa ano
            year = (
                info.get('published-print', {}).get('date-parts', [[None]])[0][0] or
                info.get('published-online', {}).get('date-parts', [[None]])[0][0] or
                info.get('issued', {}).get('date-parts', [[None]])[0][0] or
                0
            )

            new_lit = Lit(
                qtd_author=len(info.get('author', [])),
                author_names=author,
                title=title,
                public_year=year,
                doi=doi
            )
            session.add(new_lit)
            session.commit()
            return new_lit
            
        except Exception as e:
            print(f"Warning: Failed to fetch literature for DOI {doi}: {e}")
            # Retorna um registro genérico
            fallback = Lit(
                qtd_author=1,
                author_names="Unknown",
                title=f"Publication with DOI {doi}",
                public_year=0,
                doi=doi
            )
            session.add(fallback)
            session.commit()
            return fallback

    try:
        species = session.execute(select(Species).where(Species.code == args.species_code)).scalar_one_or_none()
        if not species:
            raise ValueError(f"Species '{args.species_code}' not found.")
        species_id = species.id

        # Load sequences
        seqs = session.execute(
            select(Sequence).where(Sequence.species_id == species_id, Sequence.type == "protein_coding")
        ).scalars().all()
        seq_dict = {s.name.upper(): s.id for s in seqs}

        # Parse annotation
        annotation = {}
        with open(args.sample_annotation, 'r', encoding='utf-8') as f:
            header = f.readline().strip()
            if not header:
                raise ValueError("Annotation file is empty")
            
            for line_num, line in enumerate(f, start=2):
                line = line.rstrip('\r\n')
                if not line:
                    continue
                    
                parts = [p.strip() for p in line.split('\t')]
                if len(parts) != 9:
                    print(f"Warning: Line {line_num} has {len(parts)} columns (expected 9). Skipping.")
                    continue
                    
                run, doi, desc, rep, strand, layout, po_anat, po_dev, peco = parts

                # PO anatomy is mandatory
                if not po_anat or not po_anat.strip():
                    raise ValueError(f"Line {line_num}: PO_anatomy is empty (mandatory)")

                # Verifica se amostra já existe
                existing_sample = session.execute(
                    select(Sample).where(Sample.sample_name == run, Sample.species_id == species_id)
                ).scalar_one_or_none()

                if existing_sample:
                    sample = existing_sample
                else:
                    sample = Sample(
                        sample_name=run,
                        strandness=strand,
                        layout=layout,
                        description=desc,
                        replicate=rep,
                        species_id=species_id
                    )
                    session.add(sample)
                    session.commit()

                # PO anatomy
                po_anat_clean = po_anat.strip()
                po_anat_obj = session.execute(
                    select(PlantOntology).where(PlantOntology.po_term == po_anat_clean)
                ).scalar_one_or_none()
                if not po_anat_obj:
                    raise ValueError(f"Line {line_num}: PO term '{po_anat_clean}' not found in database")

                # Verifica associação PO anatomy
                existing_po = session.execute(
                    select(SamplePO).where(
                        SamplePO.sample_id == sample.id,
                        SamplePO.po_id == po_anat_obj.id
                    )
                ).scalar_one_or_none()

                if not existing_po:
                    session.add(SamplePO(
                        sample_id=sample.id,
                        po_id=po_anat_obj.id,
                        species_id=species_id,
                        po_branch="po_anatomy"
                    ))
                    session.commit()

                # Optional PO dev stage
                if po_dev and po_dev.strip():
                    po_dev_clean = po_dev.strip()
                    po_dev_obj = session.execute(
                        select(PlantOntology).where(PlantOntology.po_term == po_dev_clean)
                    ).scalar_one_or_none()
                    if po_dev_obj:
                        existing_po_dev = session.execute(
                            select(SamplePO).where(
                                SamplePO.sample_id == sample.id,
                                SamplePO.po_id == po_dev_obj.id
                            )
                        ).scalar_one_or_none()
                        if not existing_po_dev:
                            session.add(SamplePO(
                                sample_id=sample.id,
                                po_id=po_dev_obj.id,
                                species_id=species_id,
                                po_branch="po_dev_stage"
                            ))
                            session.commit()

                # Optional PECO
                if peco and peco.strip():
                    peco_clean = peco.strip()
                    peco_obj = session.execute(
                        select(PECO).where(PECO.peco_term == peco_clean)
                    ).scalar_one_or_none()
                    if peco_obj:
                        existing_peco = session.execute(
                            select(SamplePECO).where(
                                SamplePECO.sample_id == sample.id,
                                SamplePECO.peco_id == peco_obj.id
                            )
                        ).scalar_one_or_none()
                        if not existing_peco:
                            session.add(SamplePECO(
                                sample_id=sample.id,
                                peco_id=peco_obj.id,
                                species_id=species_id
                            ))
                            session.commit()

                # Literature
                lit = get_or_create_lit(doi)
                existing_lit = session.execute(
                    select(SampleLit).where(
                        SampleLit.sample_id == sample.id,
                        SampleLit.literature_id == lit.id
                    )
                ).scalar_one_or_none()
                if not existing_lit:
                    session.add(SampleLit(
                        sample_id=sample.id,
                        literature_id=lit.id,
                        species_id=species_id
                    ))
                    session.commit()

                annotation[run] = {
                    "description": desc, "replicate": rep, "lit_doi": doi,
                    "po_anatomy": po_anat_clean, "po_anatomy_class": po_anat_obj.po_class
                }
                if po_dev and po_dev.strip():
                    if po_dev_obj:
                        annotation[run]["po_dev_stage"] = po_dev_clean
                        annotation[run]["po_dev_stage_class"] = po_dev_obj.po_class
                if peco and peco.strip():
                    if peco_obj:
                        annotation[run]["peco"] = peco_clean
                        annotation[run]["peco_class"] = peco_obj.peco_class

        # Load expression matrix
        profiles = []
        with open(args.expression_matrix, 'r', encoding='utf-8') as f:
            header_line = f.readline().strip()
            if not header_line:
                raise ValueError("Expression matrix is empty")
            colnames = [c.replace('.htseq', '') for c in header_line.split('\t')[1:]]

            order = sorted({annotation[c]["po_anatomy_class"] for c in colnames if c in annotation})

            for line_num, line in enumerate(f, start=2):
                line = line.rstrip('\r\n')
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) < 2:
                    continue
                transcript = parts[0]
                values = parts[1:]

                if len(values) != len(colnames):
                    print(f"Warning: Line {line_num} has {len(values)} values but {len(colnames)} samples. Skipping.")
                    continue

                # ✅ INICIALIZAÇÃO COMPLETA DE TODAS AS CATEGORIAS
                profile_data = {
                    'tpm': {}, 
                    'annotation': {}, 
                    'replicate': {}, 
                    'lit_doi': {},
                    'po_anatomy': {}, 
                    'po_anatomy_class': {},
                    'po_dev_stage': {}, 
                    'po_dev_stage_class': {},
                    'peco': {}, 
                    'peco_class': {}
                }
                
                for c, v in zip(colnames, values):
                    if c in annotation:
                        try:
                            profile_data['tpm'][c] = float(v)
                        except ValueError:
                            profile_data['tpm'][c] = 0.0
                        profile_data['annotation'][c] = annotation[c]['description']
                        profile_data['replicate'][c] = annotation[c]['replicate']
                        profile_data['lit_doi'][c] = annotation[c]['lit_doi']
                        profile_data['po_anatomy'][c] = annotation[c]['po_anatomy']
                        profile_data['po_anatomy_class'][c] = annotation[c]['po_anatomy_class']
                        
                        # PO dev stage (se existir nos dados)
                        if 'po_dev_stage' in annotation[c]:
                            profile_data['po_dev_stage'][c] = annotation[c]['po_dev_stage']
                            profile_data['po_dev_stage_class'][c] = annotation[c]['po_dev_stage_class']
                        
                        # PECO (se existir nos dados)
                        if 'peco' in annotation[c]:
                            profile_data['peco'][c] = annotation[c]['peco']
                            profile_data['peco_class'][c] = annotation[c]['peco_class']

                seq_id = seq_dict.get(transcript.upper())
                prof = ExprProf(
                    species_id=species_id,
                    probe=transcript,
                    sequence_id=seq_id,
                    profile=json.dumps({"order": order, "colors": [], "data": profile_data})
                )
                profiles.append(prof)
                if len(profiles) >= 300:
                    session.add_all(profiles)
                    session.commit()
                    profiles.clear()

            if profiles:
                session.add_all(profiles)
                session.commit()

        print(f"✅ Expression data for '{args.species_code}' loaded successfully ({len(annotation)} samples, {len(profiles)} profiles).")
    finally:
        session.close()

if __name__ == '__main__':
    main()
