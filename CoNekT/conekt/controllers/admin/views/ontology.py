from flask import flash
from flask_admin import expose
from markupsafe import Markup

from conekt.controllers.admin.views import AdminBaseView
from conekt.forms.admin.add_ontology import AddOntologyDataForm


class AddOntologyView(AdminBaseView):
    """
    Admin page to add ontology definitions to the database
    """
    @expose('/')
    def index(self):
        form = AddOntologyDataForm()

        return self.render('admin/add/ontology.html', form=form)