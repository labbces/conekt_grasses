from conekt import db, whooshee
from conekt.models.relationships import te_class_so
from conekt.models.relationships.te_class_so import TEClassSOAssociation

from utils.parser.sequence_ontology import SequenceOntologyParser

from collections import defaultdict
import json

SQL_COLLATION = None


@whooshee.register_model('name', 'description')
class SequenceOntology(db.Model):
    __tablename__ = 'sequence_ontologies'
    
    id = db.Column(db.Integer, primary_key=True)
    so_id = db.Column(db.String(15, collation=SQL_COLLATION), unique=True, index=True)
    name = db.Column(db.String(200, collation=SQL_COLLATION), index=True)
    description = db.Column(db.Text)
    namespace = db.Column(db.String(50, collation=SQL_COLLATION))
    is_obsolete = db.Column(db.SmallInteger, default=0)
    is_a = db.Column(db.Text)
    part_of = db.Column(db.Text)
    alias = db.Column(db.Text)  # JSON string of aliases
    
    te_classes = db.relationship('TEClass', secondary=te_class_so, lazy='dynamic')
    
    # Other properties
    #
    # te_class_associations declared in 'TEClassSOAssociation'

    def __init__(self, so_id, name, description=None, namespace=None, 
                 is_obsolete=0, is_a=None, part_of=None, alias=None):
        self.so_id = so_id
        self.name = name
        self.description = description
        self.namespace = namespace
        self.is_obsolete = is_obsolete
        self.is_a = is_a
        self.part_of = part_of
        self.alias = alias

    def __repr__(self):
        return str(self.id) + ". " + self.so_id + " - " + self.name

    @property
    def readable_namespace(self):
        """
        Converts the namespace to a readable string
        
        :return: string with readable version of the namespace
        """
        conversion = {
            'sequence_feature': 'Sequence Feature',
            'sequence_variant': 'Sequence Variant',
            'sequence_collection': 'Sequence Collection',
            'sequence_attribute': 'Sequence Attribute'
        }
        
        if self.namespace in conversion.keys():
            return conversion[self.namespace]
        else:
            return self.namespace.replace('_', ' ').title() if self.namespace else 'Unknown'

    @property
    def alias_list(self):
        """
        Returns aliases as a list
        
        :return: list of aliases or empty list if none
        """
        try:
            return json.loads(self.alias) if self.alias else []
        except (ValueError, TypeError):
            return []

    @property
    def te_class_count(self):
        """
        Returns count of te_classes associated with this SO term
        
        :return: integer count of te_classes
        """
        return self.te_classes.count()

    @property
    def sequence_count(self):
        """
        Returns count of sequences associated with this SO term via te_classes
        
        :return: integer count of sequences
        """
        from conekt.models.sequences import Sequence
        from conekt.models.te_classes import TEClass
        
        # Get all sequences from te_classes associated with this SO term
        te_class_ids = [tc.id for tc in self.te_classes.all()]
        if not te_class_ids:
            return 0
            
        # Use the association class
        from conekt.models.relationships.sequence_te_class import SequenceTEClassAssociation
        
        sequence_count = db.session.query(Sequence.id)\
            .join(SequenceTEClassAssociation, SequenceTEClassAssociation.sequence_id == Sequence.id)\
            .join(TEClass, TEClass.id == SequenceTEClassAssociation.te_class_id)\
            .filter(TEClass.id.in_(te_class_ids))\
            .distinct()\
            .count()
        
        return sequence_count

    @property  
    def species_occurrence(self):
        """
        Get list of species that have sequences associated with this SO term
        
        :return: list of species names
        """
        from conekt.models.sequences import Sequence
        from conekt.models.te_classes import TEClass
        from conekt.models.species import Species
        
        te_class_ids = [tc.id for tc in self.te_classes.all()]
        if not te_class_ids:
            return []
        
        # Use the association class
        from conekt.models.relationships.sequence_te_class import SequenceTEClassAssociation
        
        species = db.session.query(Species.name)\
            .join(Sequence, Sequence.species_id == Species.id)\
            .join(SequenceTEClassAssociation, SequenceTEClassAssociation.sequence_id == Sequence.id)\
            .join(TEClass, TEClass.id == SequenceTEClassAssociation.te_class_id)\
            .filter(TEClass.id.in_(te_class_ids))\
            .distinct()\
            .all()
        
        return [s.name for s in species]

    @property
    def te_class_stats(self):
        """
        Get statistics about te_classes and sequences associated with this SO term
        
        :return: dict with stats
        """
        stats = {
            'te_class_count': self.te_class_count,
            'sequence_count': self.sequence_count,
            'species_count': len(self.species_occurrence)
        }
        
        return stats

    @staticmethod
    def add_from_custom_file(filepath, skip_existing=True):
        """
        Add SO terms from custom file format (seq_ontology.txt)
        
        :param filepath: path to the custom SO file  
        :param skip_existing: if True skip existing SO terms
        :return: tuple with (added_count, skipped_count, updated_count)
        """
        parser = SequenceOntologyParser()
        so_entries = parser.parse_custom_format(filepath)
        
        added_count = 0
        skipped_count = 0
        updated_count = 0
        
        for entry in so_entries:
            existing = SequenceOntology.query.filter_by(so_id=entry['so_id']).first()
            
            if existing:
                if skip_existing:
                    skipped_count += 1
                    continue
                else:
                    # Update existing
                    existing.name = entry['name']
                    existing.description = entry.get('description')
                    existing.namespace = entry.get('namespace')
                    existing.alias = json.dumps(entry.get('aliases', []))
                    updated_count += 1
            else:
                # Add new SO term
                so_term = SequenceOntology(
                    so_id=entry['so_id'],
                    name=entry['name'], 
                    description=entry.get('description'),
                    namespace=entry.get('namespace'),
                    alias=json.dumps(entry.get('aliases', []))
                )
                db.session.add(so_term)
                added_count += 1
                
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
            
        return added_count, skipped_count, updated_count

    @staticmethod
    def add_so_to_te_class_associations(associations, source='manual'):
        """
        Add SO to TE class associations
        
        :param associations: list of dicts with te_class_name and so_id
        :param source: source of the annotations
        :return: count of added associations
        """
        from conekt.models.te_classes import TEClass
        
        added_count = 0
        
        for assoc in associations:
            te_class = TEClass.query.filter_by(name=assoc['te_class_name']).first()
            so_term = SequenceOntology.query.filter_by(so_id=assoc['so_id']).first()
            
            if te_class and so_term:
                # Check if association already exists
                existing = TEClassSOAssociation.query.filter_by(
                    te_class_id=te_class.id,
                    sequence_ontology_id=so_term.id
                ).first()
                
                if not existing:
                    new_assoc = TEClassSOAssociation(
                        te_class_id=te_class.id,
                        sequence_ontology_id=so_term.id,
                        evidence_code='IEA',
                        source=source
                    )
                    db.session.add(new_assoc)
                    added_count += 1
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
            
        return added_count

    def whooshee_search(self, search_string, limit=50):
        """
        Perform a full text search using Whooshee
        
        :param search_string: string to search for
        :param limit: maximum number of results
        :return: query results
        """
        return self.query.whooshee_search(search_string, limit=limit)

    def to_dict(self):
        """
        Convert to dictionary for JSON serialization
        
        :return: dictionary representation
        """
        return {
            'id': self.id,
            'so_id': self.so_id,
            'name': self.name,
            'description': self.description,
            'namespace': self.namespace,
            'readable_namespace': self.readable_namespace,
            'alias_list': self.alias_list,
            'te_class_count': self.te_class_count,
            'sequence_count': self.sequence_count,
            'species_occurrence': self.species_occurrence,
            'stats': self.te_class_stats
        }