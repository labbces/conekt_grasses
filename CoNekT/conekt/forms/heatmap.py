from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SelectMultipleField
from wtforms.validators import InputRequired
import json
from conekt.models.species import Species
from conekt.models.expression.profiles import ExpressionProfile


class HeatmapForm(FlaskForm):
    species_id = SelectField('species', coerce=int)
    probes = TextAreaField('probes', [InputRequired()])

    options = SelectField('options')

    def populate_species(self):
        self.species_id.choices = [(s.id, s.name) for s in Species.query.order_by(Species.name)]

    def populate_options(self):
        self.options.choices = [('raw', 'Raw'), ('zlog', 'zLog-ransformed'), ('rnorm', 'Row-normalized')]


class HeatmapComparableForm(FlaskForm):
    comparable_probes = TextAreaField('probes', [InputRequired()])

    comparable_options = SelectField('options')

    def populate_options(self):
        self.comparable_options.choices = [('raw', 'Raw'), ('rnorm', 'Row-normalized')]

class HeatmapPOForm(FlaskForm):
    species_id = SelectField('species', coerce=int)
    pos = SelectMultipleField('pos')
    probes = TextAreaField('probes', [InputRequired()])

    options = SelectField('options')

    def populate_species(self):
        self.species_id.choices = [(s.id, s.name) for s in Species.query.order_by(Species.name)]

    def populate_pos(self):
        self.pos.choices = [(0, "Select species first")]

    def populate_options(self):
        self.options.choices = [('raw', 'Raw'), ('zlog', 'zLog-ransformed'), ('rnorm', 'Row-normalized')]