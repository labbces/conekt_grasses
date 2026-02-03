"""
Parser for Sequence Ontology files, especially the custom seq_ontology.txt format
used for transposable elements annotation.
"""


class SequenceOntologyTerm:
    """
    Simple class to store SO term information
    """
    def __init__(self):
        self.so_term = None
        self.so_name = None
        self.so_description = None
        self.so_namespace = None
        self.aliases = None

    def print(self):
        """
        Print term information to the terminal
        """
        print(f"Term: {self.so_term}")
        print(f"Name: {self.so_name}")
        print(f"Description: {self.so_description}")
        print(f"Namespace: {self.so_namespace}")
        print(f"Aliases: {self.aliases}")
        print("---")


class SequenceOntologyParser:
    """
    Parser for Sequence Ontology files
    """
    
    def __init__(self):
        self.terms = []

    def parse_custom_format(self, filename):
        """
        Parses the custom format used in seq_ontology.txt
        Format: so_name\tso_id\taliases
        Only processes entries that come after the "####### Contents ######" section
        
        :param filename: Path to the file to parse
        """
        self.terms = []
        contents_section_found = False
        
        with open(filename, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Look for the Contents section
                if "####### Contents ######" in line:
                    contents_section_found = True
                    continue
                
                # Skip everything before the Contents section
                if not contents_section_found:
                    continue
                
                # Skip comments and empty lines
                if line.startswith('#') or not line:
                    continue
                
                # Split by tabs
                parts = line.split('\t')
                if len(parts) < 2:
                    print(f"Warning: Line {line_num} has insufficient columns, skipping: {line}")
                    continue
                
                term = SequenceOntologyTerm()
                term.so_name = parts[0].strip()
                term.so_term = parts[1].strip()
                
                # Extract aliases from third column if present
                if len(parts) > 2:
                    aliases = parts[2].strip()
                    # Clean up aliases - remove the SO name from aliases if present
                    alias_list = [a.strip() for a in aliases.split(',') if a.strip()]
                    # Remove duplicates and the SO name itself
                    alias_list = list(set(alias_list))
                    if term.so_name in alias_list:
                        alias_list.remove(term.so_name)
                    term.aliases = ','.join(alias_list) if alias_list else None
                
                # Infer namespace based on SO name patterns
                term.so_namespace = self._infer_namespace(term.so_name)
                
                # Generate basic description
                term.so_description = self._generate_description(term.so_name, term.so_term)
                
                self.terms.append(term)
        
        print(f"Parsed {len(self.terms)} SO terms from {filename}")

    def _infer_namespace(self, so_name):
        """
        Infer the namespace based on SO term name patterns
        
        :param so_name: Name of the SO term
        :return: Inferred namespace
        """
        name_lower = so_name.lower()
        
        # Transposable element related
        if any(keyword in name_lower for keyword in [
            'transposon', 'retrotransposon', 'element', 'repeat',
            'ltr', 'line', 'sine', 'dna_transposon', 'tle', 'mite'
        ]):
            return 'sequence_feature'
        
        # RNA related
        if any(keyword in name_lower for keyword in [
            'rrna', 'trna', 'mrna', 'ncrna', 'mirna', 'snrna', 'scrna'
        ]):
            return 'sequence_feature'
        
        # Structural features
        if any(keyword in name_lower for keyword in [
            'gene', 'exon', 'intron', 'utr', 'promoter', 'enhancer'
        ]):
            return 'sequence_feature'
        
        # Repeats and low complexity
        if any(keyword in name_lower for keyword in [
            'satellite', 'centromeric', 'telomeric', 'low_complexity'
        ]):
            return 'sequence_feature'
        
        # Default
        return 'sequence_feature'

    def _generate_description(self, so_name, so_term):
        """
        Generate a basic description for the SO term
        
        :param so_name: Name of the SO term
        :param so_term: SO identifier (e.g., SO:0000182)
        :return: Generated description
        """
        # Create a basic description based on the name
        name_parts = so_name.split('_')
        readable_name = ' '.join(name_parts).replace('_', ' ').title()
        
        return f"{readable_name} ({so_term}). Imported from custom sequence ontology file."

    def print_terms(self):
        """
        Print all parsed terms
        """
        for term in self.terms:
            term.print()

    def get_term_by_id(self, so_term):
        """
        Get a specific term by its SO ID
        
        :param so_term: SO identifier (e.g., SO:0000182)
        :return: SequenceOntologyTerm or None
        """
        for term in self.terms:
            if term.so_term == so_term:
                return term
        return None

    def get_terms_by_namespace(self, namespace):
        """
        Get all terms in a specific namespace
        
        :param namespace: Namespace to filter by
        :return: List of SequenceOntologyTerm objects
        """
        return [term for term in self.terms if term.so_namespace == namespace]

    def get_unique_namespaces(self):
        """
        Get all unique namespaces in the parsed terms
        
        :return: Set of namespace strings
        """
        return set(term.so_namespace for term in self.terms if term.so_namespace)

    def export_to_dict(self):
        """
        Export all terms as a list of dictionaries
        
        :return: List of dictionaries containing term data
        """
        return [
            {
                'so_term': term.so_term,
                'so_name': term.so_name,
                'so_description': term.so_description,
                'so_namespace': term.so_namespace,
                'aliases': term.aliases
            }
            for term in self.terms
        ]