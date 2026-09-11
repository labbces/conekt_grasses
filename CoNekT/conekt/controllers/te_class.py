from flask import Blueprint, redirect, url_for, render_template, Response, g
from sqlalchemy.orm import joinedload

from conekt import cache
from conekt.helpers.chartjs import prepare_doughnut
from conekt.models.te_classes import TEClass
from conekt.models.sequences import Sequence

import json

te_class = Blueprint('te_class', __name__)


@te_class.route('/')
def te_class_overview():
    """
    For lack of a better alternative redirect users to the main page
    """
    return redirect(url_for('main.screen'))


@te_class.route('/find/<te_class_name>')
@cache.cached()
def te_class_find(te_class_name):
    """
    Find a te_class based on the name and show the details for this te_class

    :param te_class_name: Name of the te_class
    """
    current_te_class = TEClass.query.filter_by(name=te_class_name).first_or_404()

    return redirect(url_for('te_class.te_class_view', te_class_id=current_te_class.id))


@te_class.route('/view/<te_class_id>')
def te_class_view(te_class_id):
    """
    Get a te_class based on the ID and show the details for this te_class

    :param te_class_id: ID of the te_class
    """
    current_te_class = TEClass.query.get_or_404(te_class_id)
    sequence_count = len(current_te_class.sequences.with_entities(Sequence.id).all())

    return render_template('te_class.html', te_class=current_te_class,
                           count=sequence_count,
                           xrefs=current_te_class.xrefs.all())


@te_class.route('/sequences/<te_class_id>/')
@te_class.route('/sequences/<te_class_id>/<int:page>')
@cache.cached()
def te_class_sequences(te_class_id, page=1):
    """
    Returns a table with sequences in the selected te_class

    :param te_class_id: Internal ID of the te_class
    :param page: Page number
    """
    sequences = TEClass.query.get(te_class_id).sequences.options(joinedload('species')).\
        order_by(Sequence.name).paginate(page,
                                         g.page_items,
                                         False).items

    return render_template('pagination/transposable_elements.html', sequences=sequences)


@te_class.route('/sequences/table/<te_class_id>')
@cache.cached()
def te_class_sequences_table(te_class_id):
    """
    Returns a csv table with sequences in the selected te_class

    :param te_class_id: Internal ID of the te_class
    """
    sequences = TEClass.query.get(te_class_id).sequences.options(joinedload('species')).order_by(Sequence.name)

    return Response(render_template('tables/sequences.csv', sequences=sequences), mimetype='text/plain')


@te_class.route('/ecc_relations/<te_class_id>/')
@te_class.route('/ecc_relations/<te_class_id>/<int:page>')
@cache.cached()
def te_class_ecc_relations(te_class_id, page=1):
    f = TEClass.query.get(te_class_id)
    relations = f.ecc_associations_paginated(page, g.page_items)

    return render_template('pagination/ecc_relations.html', relations=relations)


@te_class.route('/json/species/<te_class_id>')
@cache.cached()
def te_class_json_species(te_class_id):
    """
    Generates a JSON object with the species composition that can be rendered using Chart.js pie charts or doughnut
    plots

    :param te_class_id: ID of the te_class to render
    """
    current_te_class = TEClass.query.get_or_404(te_class_id)
    sequences = current_te_class.sequences.options(joinedload('species')).all()

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


@te_class.route('/tooltip/<te_class_id>')
@cache.cached()
def te_class_tooltip(te_class_id):
    """
    Get a te_class based on the ID and show the details for this sequence

    :param te_class_id: ID of the sequence
    """
    current_te_class = TEClass.query.get_or_404(te_class_id)

    return render_template('tooltips/te_class.html', te_class=current_te_class)


@te_class.route('/ajax/te_class/<te_class_id>')
@cache.cached()
def te_class_te_class_ajax(te_class_id):
    f = TEClass.query.get(te_class_id)

    return render_template('async/te_class_stats.html',
                           te_class_stats={k: v for k, v in f.te_class_stats.items() if str(k) != str(te_class_id)})
