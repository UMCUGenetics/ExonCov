"""Flask app forms."""
from flask_wtf import FlaskForm
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms.fields import SelectField
from wtforms.validators import InputRequired

from .models import Sample, Gene


def all_samples():
    """Query factory for all samples."""
    return Sample.query.all()


def all_genes():
    """Query factory for all genes. SLOW???."""
    return Gene.query.all()


class CustomPanelForm(FlaskForm):
    """Custom Panel form."""

    samples = QuerySelectMultipleField('Samples', validators=[InputRequired()], query_factory=all_samples)
    genes = QuerySelectMultipleField('Genes', validators=[InputRequired()], query_factory=all_genes)
    measurement_type = SelectField('Measurement type', choices=[('measurement_percentage15', '% coverage >15'), ('measurement_percentage30', '% coverage >30'), ('measurement_mean_coverage', 'Mean coverage')])
