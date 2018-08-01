"""Flask app forms."""
import re

from flask_wtf import FlaskForm
from flask_security.forms import RegisterForm
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from wtforms.fields import SelectField, TextAreaField, StringField, BooleanField
from wtforms.validators import InputRequired
from sqlalchemy import func

from .models import Sample, Gene, PanelVersion, Panel


# Query factories
def all_samples():
    """Query factory for all samples."""
    return Sample.query.all()


def all_panels():
    """Query factory for all panels."""
    return PanelVersion.query.all()


class SampleForm(FlaskForm):
    """Query samples by run or samplename field"""
    run = StringField('Run')
    sample = StringField('Sample')


class CustomPanelForm(FlaskForm):
    """Custom Panel form."""

    samples = QuerySelectMultipleField('Samples', validators=[InputRequired()], query_factory=all_samples)
    panel = QuerySelectField('Panel', validators=[], query_factory=all_panels, allow_blank=True, blank_text='Custom panel')
    gene_list = TextAreaField('Gene list', description="List of genes seperated by newline, space, ',' or ';'.", validators=[])
    measurement_type = SelectField('Measurement type', default='measurement_percentage15', choices=[
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
        self.transcript_ids = []  # Reset transcript_ids on validation

        if not FlaskForm.validate(self):
            return False

        if not self.panel.data and not self.gene_list.data:
            message = 'Panel and/or gene list must be set.'
            self.panel.errors.append(message)
            self.gene_list.errors.append(message)
            return False

        else:
            if self.panel.data:
                # Get panel transcript_ids
                self.transcript_ids.extend([transcript.id for transcript in self.panel.data.transcripts])

            if self.gene_list.data:
                # Parse gene_list
                for gene_id in re.split('[\n\r,;\t ]+', self.gene_list.data):
                    gene_id = gene_id.strip().lower()
                    if gene_id:
                        gene = Gene.query.filter(func.lower(Gene.id) == gene_id).first()
                        if gene is None:
                            self.gene_list.errors.append('Unknown gene: {0}'.format(gene_id))
                        else:
                            self.transcript_ids.append(gene.default_transcript_id)

                if self.gene_list.errors:
                    return False

        return True


class ExtendedRegisterForm(RegisterForm):
    """Extend default register form."""

    first_name = StringField('First name', validators=[InputRequired()])
    last_name = StringField('Last name', validators=[InputRequired()])


class CreatePanelForm(FlaskForm):
    """Create / Update Panel form."""

    name = StringField('Name', validators=[InputRequired()])
    gene_list = TextAreaField('Gene list', description="List of genes seperated by newline, space, ',' or ';'.", validators=[InputRequired()])
    transcript = []  # Filled in validate function

    def validate(self):
        """Extra validation, used to validate gene list and panel name."""
        # Default validation as defined in field validators
        self.transcripts = []  # Reset transcripts on validation

        if not FlaskForm.validate(self):
            return False

        if self.gene_list.data:
            # Parse gene_list
            for gene_id in re.split('[\n\r,;\t ]+', self.gene_list.data):
                gene_id = gene_id.strip().lower()
                if gene_id:
                    gene = Gene.query.filter(func.lower(Gene.id) == gene_id).first()
                    if gene is None:
                        self.gene_list.errors.append('Unknown gene: {0}'.format(gene_id))
                    elif gene.default_transcript in self.transcripts:
                        self.gene_list.errors.append('Multiple entries for gene: {0}'.format(gene_id))
                    else:
                        self.transcripts.append(gene.default_transcript)

        if self.name.data:
            panel = Panel.query.filter_by(name=self.name.data).first()
            if panel:
                self.name.errors.append('Panel already exists, use the update button on the panel page to create a new version.'.format(gene_id))

        if self.gene_list.errors or self.name.errors:
            return False

        return True


class UpdatePanelForm(FlaskForm):
    """Update Panel form."""

    gene_list = TextAreaField('Gene list', description="List of genes seperated by newline, space, ',' or ';'.", validators=[InputRequired()])
    confirm = BooleanField('Confirm')
    transcript = []  # Filled in validate function

    def validate(self):
        """Extra validation, used to validate gene list."""
        # Default validation as defined in field validators
        self.transcripts = []  # Reset transcripts on validation

        if not FlaskForm.validate(self):
            return False

        if self.gene_list.data:
            # Parse gene_list
            for gene_id in re.split('[\n\r,;\t ]+', self.gene_list.data):
                gene_id = gene_id.strip().lower()
                if gene_id:
                    gene = Gene.query.filter(func.lower(Gene.id) == gene_id).first()
                    if gene is None:
                        self.gene_list.errors.append('Unknown gene: {0}'.format(gene_id))
                    elif gene.default_transcript in self.transcripts:
                        self.gene_list.errors.append('Multiple entries for gene: {0}'.format(gene_id))
                    else:
                        self.transcripts.append(gene.default_transcript)

        if self.gene_list.errors:
            return False

        return True
