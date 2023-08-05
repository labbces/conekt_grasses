from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileField
from wtforms.validators import InputRequired, DataRequired


class AddOntologyDataForm(FlaskForm):
    po = FileField('PO')
    peco = FileField('PECO')