from flask import Blueprint, redirect, url_for, render_template, g, Response
from sqlalchemy.orm import joinedload

from conekt import cache
from conekt.models.sequence_ontology import SequenceOntology
from conekt.models.sequences import Sequence
from conekt.models.te_classes import TEClass
from conekt.models.relationships.te_class_so import TEClassSOAssociation
from conekt.helpers.chartjs import prepare_doughnut

import json

sequence_ontology = Blueprint('sequence_ontology', __name__)


@sequence_ontology.route('/')
def sequence_ontology_overview():
    """
    For lack of a better alternative redirect users to the main page
    """
    return redirect(url_for('main.screen'))


@sequence_ontology.route('/find/<term_id>')
def sequence_ontology_find(term_id):
    """
    Find SO term based on ID
    """
    so_term = SequenceOntology.query.filter_by(so_id=term_id).first()

    if so_term is not None:
        return redirect(url_for('sequence_ontology.sequence_ontology_view', so_id=so_term.id))
    else:
        return redirect(url_for('main.screen'))


@sequence_ontology.route('/view/<int:so_id>')
@cache.cached()
def sequence_ontology_view(so_id):
    """
    Get SO term details

    :param so_id: Internal ID of the SO term
    """
    so_term = SequenceOntology.query.get_or_404(so_id)
    te_class_stats = so_term.te_class_stats
    
    return render_template('sequence_ontology.html', so_term=so_term, te_class_stats=te_class_stats)


@sequence_ontology.route('/sequences/<int:so_id>/')
@sequence_ontology.route('/sequences/<int:so_id>/<int:page>')
@cache.cached()
def sequence_ontology_sequences(so_id, page=1):
    """
    Show sequences associated with SO term via te_classes

    :param so_id: Internal ID of the SO term
    :param page: page number
    """
    so_term = SequenceOntology.query.get_or_404(so_id)
    
    # Get all te_class IDs associated with this SO term
    te_class_ids = [tc.id for tc in so_term.te_classes.all()]
    
    if not te_class_ids:
        sequences = Sequence.query.filter(False).paginate(page, g.page_items, error_out=False)
    else:
        sequences = Sequence.query.join(TEClass.sequences)\
                                  .filter(TEClass.id.in_(te_class_ids))\
                                  .order_by(Sequence.name)\
                                  .paginate(page, g.page_items,
                                           error_out=False)

    return render_template('pagination/transposable_elements.html', sequences=sequences.items, so_term=so_term)


@sequence_ontology.route('/sequences/table/<int:so_id>')
@cache.cached()
def sequence_ontology_sequences_table(so_id):
    """
    Get sequences for SO term as a JSON object

    :param so_id: Internal ID of the SO term
    :return: JSON object with the sequences
    """
    so_term = SequenceOntology.query.get_or_404(so_id)
    
    # Get all te_class IDs associated with this SO term
    te_class_ids = [tc.id for tc in so_term.te_classes.all()]
    
    if not te_class_ids:
        sequences = []
    else:
        sequences = Sequence.query.join(TEClass.sequences)\
                                  .filter(TEClass.id.in_(te_class_ids))\
                                  .order_by(Sequence.name).all()

    output = {}

    for s in sequences:
        output[s.name] = {
            'url': url_for('sequence.sequence_view', sequence_id=s.id),
            'name': s.name,
            'species_id': s.species_id,
            'species_name': s.species.name,
            'type': s.type,
            'description': s.description if s.description is not None else ""
        }

    return Response(json.dumps(output), mimetype='application/json')


@sequence_ontology.route('/json/<int:so_id>')
@cache.cached()
def sequence_ontology_json(so_id):
    """
    Generates a JSON object with the species composition that can be rendered using Chart.js pie charts or doughnut
    plots for the sequence ontology term

    :param so_id: Internal ID of the SO term
    :return: JSON object with species distribution data
    """
    so_term = SequenceOntology.query.get_or_404(so_id)
    
    # Get all sequences associated with this SO term through TE classes
    te_class_ids = [tc.id for tc in so_term.te_classes.all()]
    
    if not te_class_ids:
        return Response(json.dumps({'datasets': [], 'labels': []}), mimetype='application/json')
    
    sequences = Sequence.query.join(TEClass.sequences)\
                              .filter(TEClass.id.in_(te_class_ids))\
                              .options(joinedload('species')).all()

    counts = {}

    for s in sequences:
        if s.species.code not in counts.keys():
            counts[s.species.code] = {}
            counts[s.species.code]["label"] = s.species.name
            counts[s.species.code]["color"] = s.species.color
            counts[s.species.code]["highlight"] = s.species.highlight
            counts[s.species.code]["value"] = 1
        else:
            counts[s.species.code]["value"] += 1

    plot = prepare_doughnut(counts)

    return Response(json.dumps(plot), mimetype='application/json')


@sequence_ontology.route('/modal/<int:so_id>')
@cache.cached()
def sequence_ontology_modal(so_id):
    """
    Get SO term details for modal display

    :param so_id: Internal ID of the SO term
    """
    so_term = SequenceOntology.query.get_or_404(so_id)
    
    return render_template('modals/sequence_ontology.html', so_term=so_term)