from conekt import db
from conekt.models.sequences import Sequence
from conekt.models.clades import Clade

from conekt.models.expression.cross_species_profile import CrossSpeciesExpressionProfile

from sqlalchemy.dialects.mysql import LONGTEXT

from flask import url_for
from yattag import Doc, indent
import newick

SQL_COLLATION = None


class TreeMethod(db.Model):
    __tablename__ = 'tree_methods'
    id = db.Column(db.Integer, primary_key=True)

    description = db.Column(db.Text)

    gene_family_method_id = db.Column(db.Integer,
                                      db.ForeignKey('gene_family_methods.id', ondelete='CASCADE'), index=True)

    te_class_method_id = db.Column(db.Integer,
                                      db.ForeignKey('te_class_methods.id', ondelete='CASCADE'), index=True)

    tedistill_method_id = db.Column(db.Integer,
                                      db.ForeignKey('tedistill_methods.id', ondelete='CASCADE'), index=True)

    trees = db.relationship('Tree',
                            backref=db.backref('method', lazy='joined'),
                            lazy='dynamic',
                            passive_deletes=True)


class Tree(db.Model):
    __tablename__ = 'trees'
    id = db.Column(db.Integer, primary_key=True)

    label = db.Column(db.String(50, collation=SQL_COLLATION), index=True)
    data_newick = db.Column(LONGTEXT)
    data_phyloxml = db.Column(db.Text)

    gf_id = db.Column(db.Integer, db.ForeignKey('gene_families.id', ondelete='CASCADE'), index=True)
    tec_id = db.Column(db.Integer, db.ForeignKey('te_classes.id', ondelete='CASCADE'), index=True)
    ted_id = db.Column(db.Integer, db.ForeignKey('tedistills.id', ondelete='CASCADE'), index=True)
    method_id = db.Column(db.Integer, db.ForeignKey('tree_methods.id', ondelete='CASCADE'), index=True)

    @property
    def ascii_art(self):
        """
        Returns an ascii representation of the tree. Useful for quick visualizations

        :return: string with ascii representation of the tree
        """
        tree = newick.loads(self.data_newick)[0]

        return tree.ascii_art()

    @staticmethod
    def __yattag_node(node, tag, text, line, id_to_clade, seq_to_species, seq_to_id, root=1):
        with tag('clade'):
            if root == 1:
                line('branch_length', 0.1)
            else:
                line('branch_length', node.length)
            if node.is_leaf:
                    line('name', node.name)
                    if node.name in seq_to_id.keys():
                        line('id', seq_to_id[node.name])
                    if node.name in seq_to_species.keys():
                        with tag('taxonomy'):
                            line('code', seq_to_species[node.name])
            else:
                clade_id, duplication, dup_score = node.name.split('_')

                clade_id = int(clade_id)
                duplication = True if duplication == 'D' else False
                dup_score = float(dup_score)

                if clade_id in id_to_clade.keys():
                    with tag('taxonomy'):
                        line('code', id_to_clade[clade_id])

                if duplication:
                    line('property', str(dup_score), applies_to="clade",
                         datatype="xksd:double", ref="Duplication consistency score")
                    with tag('events'):
                        line('duplications', 1)
                else:
                    with tag('events'):
                        line('speciations', 1)

                for d in node.descendants:
                    Tree.__yattag_node(d, tag, text, line, id_to_clade, seq_to_species, seq_to_id, root=0)

    @property
    def phyloxml(self):
        """
        data_phyloXML to phyloXML conversion

        :return:
        """
        # Load Tree with addition information
        tree = newick.loads(self.data_phyloxml)[0]

        # Load Additional information from the database
        clades = Clade.query.all()
        id_to_clade = {c.id: c.name for c in clades}
        seq_to_species = {}
        seq_to_id = {}
        species = []

        for s in self.sequences.all():
            seq_to_id[s.name] = s.id
            seq_to_species[s.name] = s.species.code
            if s.species not in species:
                species.append(s.species)

        csep = CrossSpeciesExpressionProfile()
        csep_data = csep.get_data(*seq_to_id.values())

        has_heatmap = False
        heatmap_order = []
        for cd in csep_data:
            if "profile" in cd.keys() and "order" in cd["profile"].keys():
                has_heatmap = True
                heatmap_order = cd["profile"]["order"]
                break

        # Start constructing PhyloXML
        doc, tag, text, line = Doc().ttl()
        with tag('phyloxml'):
            with tag('phylogeny', rooted="True"):
                # line('name', self.label)
                # line('description', "PlaNet 2.0 PhyloXML tree")
                Tree.__yattag_node(tree, tag, text, line, id_to_clade, seq_to_species, seq_to_id)

            with tag('graphs'):
                if has_heatmap:
                    with tag('graph', type="heatmap"):
                        line('name', 'Heatmap')
                        with tag('legend', show=1):
                            for label in heatmap_order:
                                with tag('field'):
                                    line('name', label)
                            with tag('gradient'):
                                line('name', 'YlGnBu')
                                line('classes', len(heatmap_order))
                        with tag('data'):
                            for cd in csep_data:
                                if "profile" in cd.keys() and "data" in cd["profile"].keys():
                                    with tag('values', **{'for': str(cd["sequence_id"])}):
                                        for label in heatmap_order:
                                            if cd["profile"]["data"][label] is not None:
                                                line('value', cd["profile"]["data"][label])
                                            else:
                                                line('value', '')

                with tag('graph', type="binary"):
                    line('name', 'Low Expression')
                    with tag('legend', show=1):
                        with tag('field'):
                            line('name', 'Low expression')
                            line('color', '0xf03b20')
                            line('shape', 'circle')

                    with tag('data'):
                        for cd in csep_data:
                            if "low_expressed" in cd.keys():
                                with tag('values', **{'for': str(cd["sequence_id"])}):
                                    line('value', cd["low_expressed"])

                with tag('graph', type="multibar"):
                    line('name', 'Expression Range')
                    with tag('legend', show=1):
                        with tag('field'):
                            line('name', 'Max. Expression (TPM)')
                            line('color', '0x664977')

                    with tag('data'):
                        for cd in csep_data:
                            if "max_expression" in cd.keys():
                                with tag('values', **{'for': str(cd["sequence_id"])}):
                                    line('value', cd["max_expression"])

            with tag('taxonomies'):
                for s in species:
                    with tag('taxonomy', code=s.code):
                        line('color', s.color.replace("#", "0x"))
                        line('name', s.name)
                        line('url', url_for('species.species_view', species_id=s.id, _external=True))

                for c in clades:
                    with tag('taxonomy', code=c.name):
                        line('color', '0x000000')
                        line('name', c.name)
                        line('url', url_for('clade.clade_view', clade_id=c.id, _external=True))

        return indent(doc.getvalue())

    @property
    def count(self):
        tree = newick.loads(self.data_newick)[0]
        return len(tree.get_leaves())

    @property
    def sequences(self):
        tree = newick.loads(self.data_newick)[0]
        sequences = [l.name for l in tree.get_leaves()]

        return Sequence.query.filter(Sequence.name.in_(sequences))

    @property
    def tree_stripped(self):
        tree = newick.loads(self.data_newick)[0]
        tree.remove_lengths()

        return newick.dumps([tree])
