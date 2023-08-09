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
        pos = []

        #the self.species_id.data in line 44 is not working
        for s in ExpressionProfile.query.filter_by(species_id=1).limit(1):
            profile = json.loads(s.profile)

            for p in profile['order']:
                pos.append((p, p.capitalize()))
                 
        self.pos.choices = pos

    def populate_options(self):
        self.options.choices = [('raw', 'Raw'), ('zlog', 'zLog-ransformed'), ('rnorm', 'Row-normalized')]