"""Flask app forms."""
import re

from flask_wtf import FlaskForm
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms.fields import SelectField, TextAreaField
from wtforms.validators import InputRequired
from sqlalchemy import func

from .models import Sample, Gene


def all_samples():
    """Query factory for all samples."""
    return Sample.query.all()


class CustomPanelForm(FlaskForm):
    """Custom Panel form."""

    samples = QuerySelectMultipleField('Samples', validators=[InputRequired()], query_factory=all_samples)
    gene_list = TextAreaField('Gene list', validators=[InputRequired()])
    measurement_type = SelectField('Measurement type', choices=[
        ('measurement_percentage10', '>10'),
        ('measurement_percentage15', '>15'),
        ('measurement_percentage20', '>20'),
        ('measurement_percentage30', '>30'),
        ('measurement_percentage50', '>50'),
        ('measurement_percentage100', '>100'),
        ('measurement_mean_coverage', 'Mean coverage')
    ])
    transcript_ids = []  # Filled in validate function

    def validate(self):
        """Extra validation, used to validate gene list."""
        # Default validation as defined in field validators
        if not FlaskForm.validate(self):
            return False

        # Parse gene_list
        self.transcript_ids = []  # Reset transcript_ids on validation
        for gene_id in re.split('[\n\r,;\t ]+', self.gene_list.data):
            gene_id = gene_id.strip().lower()
            gene = Gene.query.filter(func.lower(Gene.id) == gene_id).first()
            if gene is None:
                self.gene_list.errors.append('Unknown gene: {0}'.format(gene_id))
            else:
                self.transcript_ids.append(gene.default_transcript_id)

        if self.gene_list.errors:
            return False

        return True
