from flask import Blueprint, redirect, url_for, render_template, Response, g
from sqlalchemy.orm import joinedload

from conekt import cache
from conekt.helpers.chartjs import prepare_doughnut
from conekt.models.cazyme import CAZYme
from conekt.models.sequences import Sequence

import json

cazyme = Blueprint('cazyme', __name__)


@cazyme.route('/')
def cazyme_overview():
    """
    For lack of a better alternative redirect users to the main page
    """
    return redirect(url_for('main.screen'))


@cazyme.route('/find/<cazyme_label>')
@cache.cached()
def cazyme_find(cazyme_family):
    """
    Find a cazyme term based on the family and show the details for this term

    :param cazyme_label: Label of the CAZYme term
    """
    current_cazyme = CAZYme.query.filter_by(family=cazyme_family).first_or_404()

    return redirect(url_for('cazyme.cazyme_view', cazyme_id=current_cazyme.id))


@cazyme.route('/view/<cazyme_id>')
@cache.cached()
def cazyme_view(cazyme_id):
    """
    Get a cazyme term based on the ID and show the details for this term

    :param cazyme_id: ID of the cazyme term
    """
    current_cazyme = CAZYme.query.get_or_404(cazyme_id)
    seqIDs = {}
    sequences = current_cazyme.sequences.with_entities(Sequence.id).all()

    for s in sequences:
        seqIDs[s.id] = ""

    sequence_count = len(seqIDs)

    return render_template('cazyme.html', cazyme=current_cazyme, count=sequence_count)


@cazyme.route('/sequences/<cazyme_id>/')
@cazyme.route('/sequences/<cazyme_id>/<int:page>')
@cache.cached()
def cazyme_sequences(cazyme_id, page=1):
    """
    Returns a table with sequences with the selected cazyme

    :param cazyme_id: Internal ID of the CAZYme term
    :param page: Page number
    """
    sequences = CAZYme.query.get(cazyme_id).sequences.\
        group_by(Sequence.id).paginate(page,
                                       g.page_items,
                                       False).items

    return render_template('pagination/sequences.html', sequences=sequences)


@cazyme.route('/sequences/table/<cazyme_id>')
@cache.cached()
def cazyme_sequences_table(cazyme_id):
    sequences = CAZYme.query.get(cazyme_id).sequences.\
        group_by(Sequence.id).options(joinedload('species')).order_by(Sequence.name)

    return Response(render_template('tables/sequences.csv', sequences=sequences), mimetype='text/plain')


@cazyme.route('/json/species/<cazyme_id>')
@cache.cached()
def cazyme_json_species(cazyme_id):
    """
    Generates a JSON object with the species composition that can be rendered using Chart.js pie charts or doughnut
    plots

    :param cazyme_id: ID of the cazyme term to render
    """
    # TODO: This function can be improved with the precalculated counts !

    current_cazyme = CAZYme.query.get_or_404(cazyme_id)
    sequences = current_cazyme.sequences.options(joinedload('species')).all()

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


@cazyme.route('/json/genes/<cazyme_label>')
@cache.cached()
def cazyme_genes_find(cazyme_label):
    current_cazyme = CAZYme.query.filter_by(label=cazyme_label).first()

    if current_cazyme is not None:
        return Response(json.dumps([association.sequence_id for association in current_cazyme.sequence_associations]),
                        mimetype='application/json')
    else:
        return Response(json.dumps([]), mimetype='application/json')

@cazyme.route('/ajax/cazyme/<cazyme_id>')
@cache.cached()
def cazyme_cazyme_ajax(cazyme_id):
    current_cazyme = CAZYme.query.get(cazyme_id)

    return render_template('async/cazyme_stats.html',
                           cazyme_stats={k: v for k, v in current_cazyme.cazyme_stats.items() if str(k) != str(cazyme_id)})


@cazyme.route('/ajax/family/<cazyme_id>')
@cache.cached()
def cazyme_family_ajax(cazyme_id):
    current_cazyme = CAZYme.query.get(cazyme_id)

    return render_template('async/family_stats.html', family_stats=current_cazyme.family_stats)