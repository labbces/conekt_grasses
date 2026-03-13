#!/usr/bin/env python3

import argparse
import json
from statistics import mean
from math import sqrt, log2
from bisect import bisect

from sqlalchemy import create_engine, text
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

parser = argparse.ArgumentParser()
parser.add_argument('--species_code', required=True)
parser.add_argument('--db_admin', required=True)
parser.add_argument('--db_name', required=True)
parser.add_argument('--db_password', required=False)

args = parser.parse_args()

if args.db_password:
    db_password = args.db_password
else:
    db_password = input("Enter the database password: ")

def tau(values):
    if not values or max(values) == 0:
        return None
    n = len(values)
    mxi = max(values)
    return sum(1 - (x / mxi) for x in values) / (n - 1)

def dot_prod(a, b):
    return sum(i * j for i, j in zip(a, b))

def norm(a):
    return sqrt(sum(i ** 2 for i in a))

def expression_specificity(condition, profile):
    values = list(profile.values())
    vector = [v if k == condition else 0 for k, v in profile.items()]
    dot_product = dot_prod(values, vector)
    mul_len = norm(values) * norm(vector)
    return dot_product / mul_len if mul_len != 0 else 0

def entropy(dist):
    if not dist:
        return 0
    total = sum(dist)
    e = 0
    for d in dist:
        if d > 0:
            p = d / total
            e += -p * log2(p)
    return e

def entropy_from_values(values, num_bins=20):
    if not values:
        return 0
    v_max = max(values)
    if v_max == 0:
        return 0
    n_values = [v / v_max for v in values]
    hist = [0] * num_bins
    bins = [b / num_bins for b in range(num_bins + 1)]
    for v in n_values:
        idx = min(bisect(bins, v) - 1, num_bins - 1)
        hist[idx] += 1
    return entropy(hist)

def calculate_specificities(species_code, engine, session, batch_size=400):
    # Get species_id
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id FROM species WHERE code = :code"), {"code": species_code}).first()
        if not result:
            print(f"Species {species_code} not found!")
            exit(1)
        species_id = result[0]

    # Step 1: Get all literature items first
    literature_map = {}
    with engine.connect() as conn:
        lit_rows = conn.execute(text("SELECT id, author_names, public_year, doi FROM literature")).fetchall()
        for lit_id, author, year, doi in lit_rows:
            literature_map[doi] = (lit_id, author, year)

    # Step 2: Process all profiles in ONE PASS
    print("🔍 Processing all profiles in single pass...")
    offset = 0
    total_processed = 0
    
    # Data structures to accumulate results
    method_cache = {}  # (doi, category) -> method_id
    specificity_buffer = []  # buffer for bulk inserts

    while True:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, profile FROM expression_profiles 
                WHERE species_id = :species_id 
                LIMIT :limit OFFSET :offset
            """), {
                "species_id": species_id,
                "limit": batch_size,
                "offset": offset
            }).fetchall()
        
        if not rows:
            break

        for profile_id, profile_json in rows:
            profile_data = json.loads(profile_json)
            
            if 'data' not in profile_data or 'lit_doi' not in profile_data['data']:
                continue

            # Group TPM by (DOI, category, condition)
            tpm_groups = {}
            
            for sample_id, tpm_val in profile_data['data']['tpm'].items():
                doi = profile_data['data']['lit_doi'].get(sample_id)
                if not doi:
                    continue
                
                for cat_key in ['po_anatomy_class', 'po_dev_stage_class']:
                    if cat_key in profile_data['data'] and sample_id in profile_data['data'][cat_key]:
                        condition = profile_data['data'][cat_key][sample_id]
                        key = (doi, cat_key, condition)
                        if key not in tpm_groups:
                            tpm_groups[key] = []
                        tpm_groups[key].append(tpm_val)

            # Calculate specificity for each (DOI, category)
            for (doi, cat_key, _), _ in tpm_groups.items():
                # Group by condition for this (DOI, category)
                cond_tpm = {}
                for (d, c, cond), tpms in tpm_groups.items():
                    if d == doi and c == cat_key:
                        if cond not in cond_tpm:
                            cond_tpm[cond] = []
                        cond_tpm[cond].extend(tpms)
                
                if len(cond_tpm) < 2:
                    continue
                
                # Create method if not exists
                method_key = (doi, cat_key)
                if method_key not in method_cache:
                    if doi not in literature_map:
                        continue
                    lit_id, author, year = literature_map[doi]
                    cat_name = cat_key.replace('_class', '')
                    new_method = ExpressionSpecificityMethod()
                    new_method.species_id = species_id
                    new_method.description = f"{cat_name} ({author}, {year} - {doi})"
                    new_method.literature_id = lit_id
                    new_method.data_type = 'condition'
                    new_method.menu_order = 0
                    new_method.conditions = json.dumps(list(cond_tpm.keys()))
                    session.add(new_method)
                    session.commit()
                    method_cache[method_key] = new_method.id
                    print(f"✅ Created method: {new_method.description}")
                
                method_id = method_cache[method_key]
                
                # Calculate means
                means = {cond: mean(vals) for cond, vals in cond_tpm.items()}
                profile_tau = tau(list(means.values()))
                profile_entropy = entropy_from_values(list(means.values()))
                
                # Find best condition
                best_score = -1
                best_cond = None
                for cond in means:
                    score = expression_specificity(cond, means)
                    if score > best_score:
                        best_score = score
                        best_cond = cond
                
                if best_cond is not None:
                    spec = ExpressionSpecificity(
                        profile_id=profile_id,
                        condition=best_cond,
                        score=best_score,
                        entropy=profile_entropy,
                        tau=profile_tau,
                        method_id=method_id,
                    )
                    specificity_buffer.append(spec)
                    
                    # Bulk insert every 400 records
                    if len(specificity_buffer) >= 400:
                        session.add_all(specificity_buffer)
                        session.commit()
                        specificity_buffer = []
                        print(f"  → Committed 400 specificities (total processed: {total_processed + 400})")

            total_processed += 1
            if total_processed % 10000 == 0:
                print(f"  → Processed {total_processed} profiles")

        offset += len(rows)

    # Final commit
    if specificity_buffer:
        session.add_all(specificity_buffer)
        session.commit()
        print(f"  → Committed final {len(specificity_buffer)} specificities")

    print(f"\n🎉 Completed! Total profiles processed: {total_processed}")

# Setup DB
db_admin = args.db_admin
db_name = args.db_name
engine = create_engine(f"mysql+pymysql://{db_admin}:{db_password}@localhost/{db_name}", echo=False)
Base = automap_base()
Base.prepare(engine, reflect=True)

Species = Base.classes.species
ExpressionSpecificityMethod = Base.classes.expression_specificity_method
ExpressionSpecificity = Base.classes.expression_specificity
ExpressionProfile = Base.classes.expression_profiles
LiteratureItem = Base.classes.literature

Session = sessionmaker(bind=engine)
session = Session()

# Run
calculate_specificities(args.species_code, engine, session, batch_size=400)

session.close()
print("✅ Specificity calculation finished.")
