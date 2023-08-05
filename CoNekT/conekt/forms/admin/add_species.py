from flask_wtf import FlaskForm
from wtforms import StringField, RadioField, TextAreaField, IntegerField, SelectField
from flask_wtf.file import FileRequired, FileField
from wtforms.validators import InputRequired, DataRequired


class AddSpeciesForm(FlaskForm):
    name = StringField('Scientific Name', [InputRequired()])
    code = StringField('Code', [InputRequired()])

    data_type = RadioField('Data type',
                           choices=[('genome', 'Genome'), ('transcriptome', 'Transcriptome')],
                           default='genome')

    color = StringField('Color', [InputRequired()])
    highlight = StringField('Highlight', [InputRequired()])

    description = TextAreaField('Description')

    # adding the source
    source = SelectField('Source', coerce=str, choices=[('Phytozome','Phytozome'), 
                                                        ('NCBI','NCBI'), ('CoGe','CoGe'),
                                                        ('PLAZA','PLAZA'), ('LabBCES','LabBCES')])

    # adding literature information
    literature = RadioField('Add Literature?', choices=[('yes', 'Yes'), ('no', 'No')], default='no')

    doi = StringField('DOI')

    fasta_cds = FileField('Fasta')

    fasta_rna = FileField('Fasta')

    genome_version = StringField('Genome/Transcriptome version', [InputRequired()])



