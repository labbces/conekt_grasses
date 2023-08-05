import os
from tempfile import mkstemp

from flask import request, flash, url_for
from conekt.extensions import admin_required
from markupsafe import Markup
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from conekt.controllers.admin.controls import admin_controls
from conekt.forms.admin.add_ontology import AddOntologyDataForm
from conekt.models.ontologies import PlantOntology, PlantExperimentalConditionsOntology


@admin_controls.route('/add/ontology', methods=['POST'])
@admin_required
def add_ontology():
    """
    #TODO: Add documentation
    :return: Redirect to admin panel interface
    """
    form = AddOntologyDataForm(request.form)

    if request.method == 'POST' and form.validate():
        po_data = request.files[form.po.name].read()
        peco_data = request.files[form.peco.name].read()

        if po_data != b'' or peco_data != b'':
            po_fd, po_temp_path = mkstemp()
            peco_fd, peco_temp_path = mkstemp()

            # Add PO
            with open(po_temp_path, 'wb') as po_writer:
                po_writer.write(po_data)

            PlantOntology.add_tabular_po(po_temp_path, empty=True, compressed=False)

            # Add PECO
            with open(peco_temp_path, 'wb') as peco_writer:
                peco_writer.write(peco_data)
            
            PlantExperimentalConditionsOntology.add_tabular_peco(peco_temp_path, empty=True, compressed=False)

            os.close(po_fd)
            os.remove(po_temp_path)
            os.close(peco_fd)
            os.remove(peco_temp_path)
            flash('Ontologies data added.', 'success')
        else:
            flash('No ontology data selected, skipping ...', 'warning')
        return redirect(url_for('admin.index'))
    else:
        if not form.validate():
            flash('Unable to validate data, potentially missing fields', 'danger')
            return redirect(url_for('admin.index'))
        else:
            abort(405)