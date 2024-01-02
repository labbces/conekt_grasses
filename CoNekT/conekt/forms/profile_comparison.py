from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, BooleanField, SelectMultipleField
from wtforms.validators import InputRequired

from conekt.models.species import Species

class ProfileComparisonForm(FlaskForm):
    species_id = SelectField('Species', coerce=int)
    literature = SelectField('Literature', coerce=int, choices=[])
    probes = TextAreaField('probes', [InputRequired()])
    normalize = BooleanField('Normalize plots?')

    def populate_form(self):
        self.species_id.choices = [(0, "Select species")] + [(s.id, s.name) for s in Species.query.order_by(Species.name)]