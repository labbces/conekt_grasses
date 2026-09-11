from flask import Blueprint, redirect, url_for, render_template, Response, g
from sqlalchemy.orm import joinedload

from conekt import cache
from conekt.helpers.chartjs import prepare_doughnut
from conekt.models.tr import TranscriptionRegulator
from conekt.models.sequences import Sequence

import json

tr = Blueprint('tr', __name__)


@tr.route('/')
def tr_overview():
    """
    For lack of a better alternative redirect users to the main page
    """
    return redirect(url_for('main.screen'))


@tr.route('/find/<tr_label>')
@cache.cached()
def tr_find(tr_family):
    """
    Find a tr term based on the family and show the details for this term

    :param tr_label: Label of the TranscriptionRegulator term
    """
    current_tr = TranscriptionRegulator.query.filter_by(family=tr_family).first_or_404()

    return redirect(url_for('tr.tr_view', tr_id=current_tr.id))


@tr.route('/view/<tr_id>')
@cache.cached()
def tr_view(tr_id):
    """
    Get a tr term based on the ID and show the details for this term

    :param tr_id: ID of the tr term
    """
    current_tr = TranscriptionRegulator.query.get_or_404(tr_id)
    seqIDs = {}
    sequences = current_tr.sequences.with_entities(Sequence.id).all()

    for s in sequences:
        seqIDs[s.id] = ""

    sequence_count = len(seqIDs)

    return render_template('tr.html', tr=current_tr, count=sequence_count)


@tr.route('/sequences/<tr_id>/')
@tr.route('/sequences/<tr_id>/<int:page>')
@cache.cached()
def tr_sequences(tr_id, page=1):
    """
    Returns a table with sequences with the selected tr

    :param tr_id: Internal ID of the TranscriptionRegulator term
    :param page: Page number
    """
    sequences = TranscriptionRegulator.query.get(tr_id).sequences.\
        group_by(Sequence.id).paginate(page,
                                       g.page_items,
                                       False).items

    return render_template('pagination/sequences.html', sequences=sequences)


@tr.route('/sequences/table/<tr_id>')
@cache.cached()
def tr_sequences_table(tr_id):
    sequences = TranscriptionRegulator.query.get(tr_id).sequences.\
        group_by(Sequence.id).options(joinedload('species')).order_by(Sequence.name)

    return Response(render_template('tables/sequences.csv', sequences=sequences), mimetype='text/plain')


@tr.route('/json/species/<tr_id>')
@cache.cached()
def tr_json_species(tr_id):
    """
    Generates a JSON object with the species composition that can be rendered using Chart.js pie charts or doughnut
    plots

    :param tr_id: ID of the tr term to render
    """
    # TODO: This function can be improved with the precalculated counts !

    current_tr = TranscriptionRegulator.query.get_or_404(tr_id)
    sequences = current_tr.sequences.options(joinedload('species')).all()

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


@tr.route('/json/genes/<tr_label>')
@cache.cached()
def tr_genes_find(tr_label):
    current_tr = TranscriptionRegulator.query.filter_by(label=tr_label).first()

    if current_tr is not None:
        return Response(json.dumps([association.sequence_id for association in current_tr.sequence_associations]),
                        mimetype='application/json')
    else:
        return Response(json.dumps([]), mimetype='application/json')

@tr.route('/ajax/tr/<tr_id>')
@cache.cached()
def tr_tr_ajax(tr_id):
    current_tr = TranscriptionRegulator.query.get(tr_id)

    return render_template('async/tr_stats.html',
                           tr_stats={k: v for k, v in current_tr.tr_stats.items() if str(k) != str(tr_id)})


@tr.route('/ajax/family/<tr_id>')
@cache.cached()
def tr_family_ajax(tr_id):
    current_tr = TranscriptionRegulator.query.get(tr_id)

    return render_template('async/family_stats.html', family_stats=current_tr.family_stats)