import os
from tempfile import mkstemp

from flask import request, flash, url_for
from conekt.extensions import admin_required
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from conekt.controllers.admin.controls import admin_controls
from conekt.forms.admin.add_species import AddSpeciesForm
from conekt.models.sequences import Sequence
from conekt.models.species import Species
from conekt.models.literature import LiteratureItem

@admin_controls.route('/add/species', methods=['POST'])
@admin_required
def add_species():
    """
    Adds a species to the species table and adds sequences for that species to the sequence table based on the fasta
    file provided.

    :return: Redirect to admin panel interface
    """
    form = AddSpeciesForm(request.form)

    if request.method == 'POST' and form.validate():

        fasta_data_cds = request.files[form.fasta_cds.name].read()

        fasta_data_rna = request.files[form.fasta_rna.name].read()

        if not fasta_data_cds or not fasta_data_rna:
            flash('Missing File. Please, upload both Fasta Files before submission.', 'danger')
            return redirect(url_for('admin.add.species.index'))

        # verify if literature option was inserted or not
        literature_answer = request.form.get('literature')

        literature_id = None

        if literature_answer == 'yes':
            doi=request.form.get('doi')
            # Add literature (or return id of existing literature)
            literature_id = LiteratureItem.add(doi=doi)

        # Add species (or return id of existing species)
        species_id = Species.add(request.form.get('code'),
                                request.form.get('name'),
                                data_type=request.form.get('data_type'),
                                color='#' + request.form.get('color'),
                                highlight='#' + request.form.get('highlight'),
                                description=request.form.get('description'),
                                source=request.form.get('source'),
                                literature_id = literature_id,
                                genome_version = request.form.get('genome_version'))

        # Add CDS Sequences
        fd, temp_path = mkstemp()

        compressed_cds = 'gzip' in request.files[form.fasta_cds.name].content_type

        with open(temp_path, 'wb') as fasta_writer:
            fasta_writer.write(fasta_data_cds)

        sequence_count_cds = Sequence.add_from_fasta(temp_path, species_id, compressed=compressed_cds)

        os.close(fd)
        os.remove(temp_path)

        # Add RNA Sequences
        fd, temp_path = mkstemp()

        compressed_rna = 'gzip' in request.files[form.fasta_rna.name].content_type

        with open(temp_path, 'wb') as fasta_writer:
            fasta_writer.write(fasta_data_rna)

        sequence_count_rna = Sequence.add_from_fasta(temp_path, species_id, compressed=compressed_rna,
                                                      sequence_type='RNA')
        
        os.close(fd)
        os.remove(temp_path)

        flash('Added species %s with %d CDS sequences' % (request.form.get('name'), sequence_count_cds), 'success')
        flash('Added species %s with %d RNA sequences' % (request.form.get('name'), sequence_count_rna), 'success')
        return redirect(url_for('admin.index'))
    else:
        if not form.validate():
            flash('Unable to validate data, potentially missing fields', 'danger')
            return redirect(url_for('admin.index'))
        else:
            abort(405)
