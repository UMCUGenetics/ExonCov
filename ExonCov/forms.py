"""Flask app forms."""
from flask_wtf import FlaskForm
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
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

    sample = QuerySelectField('Sample', validators=[InputRequired()], query_factory=all_samples)
    genes = QuerySelectMultipleField('Genes', validators=[InputRequired()], query_factory=all_genes)
