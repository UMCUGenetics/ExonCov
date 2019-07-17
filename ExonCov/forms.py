"""Flask app forms."""
import re

from flask_wtf import FlaskForm
from flask_security.forms import RegisterForm
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from wtforms.fields import SelectField, TextAreaField, StringField, BooleanField
from wtforms import validators

from .models import Sample, SampleSet, Gene, PanelVersion, Panel


# Query factories
def all_samples():
    """Query factory for all samples."""
    return Sample.query.all()


def active_sample_sets():
    """Query factory for active sample sets."""
    return SampleSet.query.filter_by(active=True).all()


def all_panels():
    """Query factory for all panels."""
    return PanelVersion.query.filter_by(active=True).filter_by(validated=True).all()


def parse_gene_list(gene_list, transcripts=[]):
    """Parse data from gene_list form field"""
    errors = []
    for gene_id in re.split('[\n\r,;\t ]+', gene_list):
        gene_id = gene_id.strip()
        if gene_id:
            gene = Gene.query.filter(Gene.id == gene_id).first()
            if gene is None:
                errors.append('Unknown gene: {0}'.format(gene_id))
            elif gene.default_transcript in transcripts:
                errors.append('Multiple entries for gene: {0}'.format(gene_id))
            else:
                transcripts.append(gene.default_transcript)
    return errors, transcripts


class SampleForm(FlaskForm):
    """Query samples by run or samplename field"""
    sample = StringField('Sample')
    project = StringField('Project')
    run = StringField('Sequencing run')


class CustomPanelNewForm(FlaskForm):
    """Custom Panel New form."""

    sample_set = QuerySelectField('Sample sets', query_factory=active_sample_sets, allow_blank=True, blank_text='None')
    samples = QuerySelectMultipleField('Samples', query_factory=all_samples, allow_blank=True, blank_text='None')
    panel = QuerySelectField('Panel', query_factory=all_panels, allow_blank=True, blank_text='None')
    gene_list = TextAreaField('Gene list', description="List of genes seperated by newline, space, ',' or ';'.", validators=[])
    research_number = StringField('Test reference number', description="Provide a test reference number (onderzoeksnummer) for INC99 tests.")
    comments = TextAreaField('Comments', description="Provide a short description.")
    transcripts = []  # Filled in validate function

    def validate(self):
        """Extra validation, used to validate gene list."""
        # Default validation as defined in field validators
        self.transcripts = []  # Reset transcripts on validation

        if not FlaskForm.validate(self):
            return False

        # Parse Samples and Sample sets
        if not self.samples.data and not self.sample_set.data:
            message = 'Sample(s) and/or sample set must be set.'
            self.samples.errors.append(message)
            self.sample_set.errors.append(message)
            return False
        elif self.samples.data and self.sample_set.data:
            sample_ids = [sample.id for sample in self.samples.data]
            for sample in self.sample_set.data.samples:
                if sample.id in sample_ids:
                    message = 'Sample {0} is already present in sample set.'.format(sample.name)
                    self.samples.errors.append(message)
                    return False

        # Parse panels and genes
        if not self.panel.data and not self.gene_list.data:
            message = 'Panel and/or gene list must be set.'
            self.panel.errors.append(message)
            self.gene_list.errors.append(message)
            return False
        else:
            if self.panel.data:
                # Get panel transcript_ids
                self.transcripts.extend([transcript for transcript in self.panel.data.transcripts])

            if self.gene_list.data:
                # Parse gene_list
                errors, self.transcripts = parse_gene_list(self.gene_list.data, self.transcripts)
                if errors:
                    self.gene_list.errors.extend(errors)
                    return False

        # Parse research_number and comments
        if not self.research_number.data and not self.comments.data:
            message = 'Please provide a research number or a short description in the comments field.'
            self.research_number.errors.append(message)
            self.comments.errors.append(message)
            return False

        return True


class MeasurementTypeForm(FlaskForm):
    """Custom Panel form."""

    measurement_type = SelectField('Measurement type', default='measurement_percentage15', choices=[
        ('measurement_percentage10', '>10'),
        ('measurement_percentage15', '>15'),
        ('measurement_percentage20', '>20'),
        ('measurement_percentage30', '>30'),
        ('measurement_percentage50', '>50'),
        ('measurement_percentage100', '>100'),
        ('measurement_mean_coverage', 'Mean coverage')
    ])


class ExtendedRegisterForm(RegisterForm):
    """Extend default register form."""

    first_name = StringField('First name', validators=[validators.InputRequired()])
    last_name = StringField('Last name', validators=[validators.InputRequired()])


class CreatePanelForm(FlaskForm):
    """Create Panel form."""

    name = StringField('Name', validators=[validators.InputRequired()])
    gene_list = TextAreaField('Gene list', description="List of genes seperated by newline, space, ',' or ';'.", validators=[validators.InputRequired()])
    comments = TextAreaField('Comments', description="Provide a short description.", validators=[validators.InputRequired()])
    transcript = []  # Filled in validate function

    def validate(self):
        """Extra validation, used to validate gene list and panel name."""
        # Default validation as defined in field validators
        self.transcripts = []  # Reset transcripts on validation

        if not FlaskForm.validate(self):
            return False

        if self.gene_list.data:
            # Parse gene_list
            errors, self.transcripts = parse_gene_list(self.gene_list.data, self.transcripts)
            if errors:
                self.gene_list.errors.extend(errors)
                return False

        if self.name.data:
            panel = Panel.query.filter_by(name=self.name.data).first()
            if panel:
                self.name.errors.append('Panel already exists, use the update button on the panel page to create a new version.')

        if self.gene_list.errors or self.name.errors:
            return False

        return True


class UpdatePanelForm(FlaskForm):
    """Update Panel form."""

    gene_list = TextAreaField('Gene list', description="List of genes seperated by newline, space, ',' or ';'.", validators=[validators.InputRequired()])
    comments = TextAreaField('Comments', description="Provide a short description.", validators=[validators.InputRequired()])
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
            errors, self.transcripts = parse_gene_list(self.gene_list.data, self.transcripts)
            if errors:
                self.gene_list.errors.extend(errors)
                return False

        if self.gene_list.errors:
            return False

        return True


class PanelVersionEditForm(FlaskForm):
    """PanelVersion edit form."""

    comments = TextAreaField('Comments', description="Provide a short description.", validators=[validators.InputRequired()])
    active = BooleanField('Active')
    validated = BooleanField('Validated')
