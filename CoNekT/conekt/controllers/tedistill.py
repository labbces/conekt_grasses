from flask import Blueprint, redirect, url_for, render_template, Response, g, make_response
from sqlalchemy.orm import joinedload, undefer, noload

from conekt import cache
from conekt.helpers.chartjs import prepare_doughnut
from conekt.models.tedistills import TEdistill
from conekt.models.sequences import Sequence

import json

tedistill = Blueprint('tedistill', __name__)


@tedistill.route('/')
def tedistill_overview():
    """
    For lack of a better alternative redirect users to the main page
    """
    return redirect(url_for('main.screen'))


@tedistill.route('/find/<tedistill_name>')
@cache.cached()
def tedistill_find(tedistill_name):
    """
    Find a gene tedistill based on the name and show the details for this tedistill

    :param tedistill_name: Name of the gene tedistill
    """
    current_tedistill = TEdistill.query.filter_by(name=tedistill_name).first_or_404()

    return redirect(url_for('tedistill.tedistill_view', tedistill_id=current_tedistill.id))


@tedistill.route('/view/<tedistill_id>')
def tedistill_view(tedistill_id):
    """
    Get a gene tedistill based on the ID and show the details for this tedistill

    :param tedistill_id: ID of the gene tedistill
    """
    current_tedistill = TEdistill.query.get_or_404(tedistill_id)
    sequence_count = len(current_tedistill.sequences.with_entities(Sequence.id).all())

    return render_template('tedistill.html', tedistill=current_tedistill,
                           count=sequence_count,
                           xrefs=current_tedistill.xrefs.all())


@tedistill.route('/sequences/<tedistill_id>/')
@tedistill.route('/sequences/<tedistill_id>/<int:page>')
@cache.cached()
def tedistill_sequences(tedistill_id, page=1):
    """
    Returns a table with sequences in the selected tedistill

    :param tedistill_id: Internal ID of the tedistill
    :param page: Page number
    """
    sequences = TEdistill.query.get(tedistill_id).sequences.options(joinedload('species')).\
        order_by(Sequence.name).paginate(page,
                                         g.page_items,
                                         False).items

    return render_template('pagination/transposable_elements.html', sequences=sequences)


@tedistill.route('/sequences/table/<tedistill_id>')
@cache.cached()
def tedistill_sequences_table(tedistill_id):
    """
    Returns a csv table with sequences in the selected tedistill

    :param tedistill_id: Internal ID of the tedistill
    """
    sequences = TEdistill.query.get(tedistill_id).sequences.options(joinedload('species')).order_by(Sequence.name)

    return Response(render_template('tables/sequences.csv', sequences=sequences), mimetype='text/plain')


@tedistill.route('/ecc_relations/<tedistill_id>/')
@tedistill.route('/ecc_relations/<tedistill_id>/<int:page>')
@cache.cached()
def tedistill_ecc_relations(tedistill_id, page=1):
    f = TEdistill.query.get(tedistill_id)
    relations = f.ecc_associations_paginated(page, g.page_items)

    return render_template('pagination/ecc_relations.html', relations=relations)


@tedistill.route('/json/species/<tedistill_id>')
@cache.cached()
def tedistill_json_species(tedistill_id):
    """
    Generates a JSON object with the species composition that can be rendered using Chart.js pie charts or doughnut
    plots

    :param tedistill_id: ID of the tedistill to render
    """
    current_tedistill = TEdistill.query.get_or_404(tedistill_id)
    sequences = current_tedistill.sequences.options(joinedload('species')).all()

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


@tedistill.route('/tooltip/<tedistill_id>')
@cache.cached()
def tedistill_tooltip(tedistill_id):
    """
    Get a tedistill based on the ID and show the details for this sequence

    :param tedistill_id: ID of the sequence
    """
    current_tedistill = TEdistill.query.get_or_404(tedistill_id)

    return render_template('tooltips/tedistill.html', tedistill=current_tedistill)

@tedistill.route('/modal/coding/<tedistill_id>')
def sequence_modal_coding(tedistill_id):
	"""
	Returns the coding sequence in a modal

	:param tedistill_id: ID of the tedistill
	:return: Response with the fasta file
	"""
	current_tedistill = TEdistill.query\
		.options(undefer('representative_sequence'))\
		.options(noload('xrefs'))\
		.get_or_404(tedistill_id)

	return render_template('modals/tedistill.html', tedistill=current_tedistill)

@tedistill.route('/fasta/coding/<tedistill_id>')
def sequence_fasta_coding(tedistill_id):
	"""
	Returns the coding sequence as a downloadable fasta file

	:param sequence_id: ID of the sequence
	:return: Response with the fasta file
	"""

	current_tedistill = TEdistill.query\
		.options(undefer('representative_sequence'))\
		.options(noload('xrefs'))\
		.get_or_404(tedistill_id)

	fasta = ">" + current_tedistill.name + "\n" + current_tedistill.representative_sequence + "\n"
	response = make_response(fasta)
	response.headers["Content-Disposition"] = "attachment; filename=" + current_tedistill.name + ".rep_seq.fasta"
	response.headers['Content-type'] = 'text/plain'

	return response

@tedistill.route('/ajax/tedistill/<tedistill_id>')
@cache.cached()
def tedistill_tedistill_ajax(tedistill_id):
    f = TEdistill.query.get(tedistill_id)

    return render_template('async/tedistill_stats.html',
                           tedistill_stats={k: v for k, v in f.tedistill_stats.items() if str(k) != str(tedistill_id)})
