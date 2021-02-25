"""Flask app forms."""
import re

from flask_wtf import FlaskForm
from flask_security.forms import RegisterForm
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from wtforms.fields import SelectField, TextAreaField, StringField, BooleanField, FloatField
from wtforms import validators

from .models import Sample, SampleSet, Gene, GeneAlias, PanelVersion, Panel


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


def get_gene(gene_id):
    """Find gene or gene aliases."""
    error = ''
    gene = Gene.query.get(gene_id)

    # Find possible gene alias if gene not found
    if not gene:
        gene_aliases = GeneAlias.query.filter_by(id=gene_id).all()
        if gene_aliases:
            error = 'Unkown gene: {0}. Possible aliases: {1}. Please check before using alias.'.format(
                gene_id,
                ', '.join([gene_alias.gene_id for gene_alias in gene_aliases])
            )
        else:
            error = 'Unknown gene: {0}.'.format(gene_id)

    return gene, error


def parse_gene_list(gene_list, transcripts=[]):
    """Parse data from gene_list form field"""
    errors = []
    for gene_id in re.split('[\n\r,;\t ]+', gene_list):
        gene_id = gene_id.strip()
        if gene_id:
            gene, error = get_gene(gene_id)

            if not gene:
                errors.append(error)
            elif gene.default_transcript in transcripts:
                errors.append('Multiple entries for gene: {0}.'.format(gene_id))
            else:
                transcripts.append(gene.default_transcript)
    return errors, transcripts


def parse_core_gene_list(gene_list, genes=[]):
    """Parse data from gene_list form field"""
    errors = []
    for gene_id in re.split('[\n\r,;\t ]+', gene_list):
        gene_id = gene_id.strip()
        if gene_id:
            gene, error = get_gene(gene_id)
            if not gene:
                errors.append(error)
            elif gene in genes:
                errors.append('Multiple entries for gene: {0}.'.format(gene_id))
            else:
                genes.append(gene)
    return errors, genes


class SampleForm(FlaskForm):
    """Query samples by run or samplename field"""
    sample = StringField('Sample')
    project = StringField('Project')
    run = StringField('Sequencing run')


class CustomPanelForm(FlaskForm):
    """Query custom panels by test reference number or comments field"""
    search = StringField('Search')


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
    gene_list = TextAreaField(
        'Gene list',
        description="List of genes seperated by newline, space, ',' or ';'.",
        validators=[validators.InputRequired()]
    )
    core_gene_list = TextAreaField('Core gene list', description="List of core genes seperated by newline, space, ',' or ';'.")
    coverage_requirement_15 = FloatField('Minimal % 15x', default=99, validators=[validators.InputRequired()])
    disease_description_eng = StringField('Disease description', validators=[validators.InputRequired()])
    disease_description_nl = StringField('Ziekteomschrijving', validators=[validators.InputRequired()])
    patientfolder_alissa = StringField('Alissa', validators=[validators.InputRequired()])
    clinic_contact = StringField('Clinic contact(s)', validators=[validators.InputRequired()])
    staff_member = StringField('Staff member', validators=[validators.InputRequired()])
    comments = TextAreaField('Comments', description="Provide a short description.", validators=[validators.InputRequired()])

    transcript = []  # Filled in validate function
    core_genes = []

    def validate(self):
        """Additional validation, used to validate gene list and panel name."""

        # Reset on validation
        self.transcripts = []
        self.core_genes = []

        if not FlaskForm.validate(self):
            return False

        if self.gene_list.data:
            # Parse gene_list
            errors, self.transcripts = parse_gene_list(self.gene_list.data, self.transcripts)
            if errors:
                self.gene_list.errors.extend(errors)

        if self.core_gene_list.data:
            # Parse gene_list
            errors, self.core_genes = parse_core_gene_list(self.core_gene_list.data, self.core_genes)
            for gene in self.core_genes:
                if gene.id not in self.gene_list.data:
                    errors.append('Core gene {0} not found in gene list.'.format(gene.id))
            if errors:
                self.core_gene_list.errors.extend(errors)

        if self.name.data:
            panel = Panel.query.filter_by(name=self.name.data).first()
            if panel:
                self.name.errors.append('Panel already exists, use the update button on the panel page to create a new version.')

        if self.gene_list.errors or self.core_gene_list.errors or self.name.errors:
            return False

        return True


class PanelNewVersionForm(FlaskForm):
    """New panel version form."""

    gene_list = TextAreaField(
        'Gene list',
        description="List of genes seperated by newline, space, ',' or ';'.",
        validators=[validators.InputRequired()]
    )
    core_gene_list = TextAreaField('Core gene list', description="List of core genes seperated by newline, space, ',' or ';'.")
    coverage_requirement_15 = FloatField('Minimal % 15x')
    comments = TextAreaField('Comments', description="Provide a short description.", validators=[validators.InputRequired()])
    confirm = BooleanField('Confirm')

    # Filled in validate function
    transcript = []
    core_genes = []

    def validate(self):
        """Additional validation, used to validate gene list."""

        # Reset before validation
        self.transcripts = []
        self.core_genes = []

        if not FlaskForm.validate(self):
            return False

        if self.gene_list.data:
            # Parse gene_list
            errors, self.transcripts = parse_gene_list(self.gene_list.data, self.transcripts)
            if errors:
                self.gene_list.errors.extend(errors)

        if self.core_gene_list.data:
            # Parse gene_list
            errors, self.core_genes = parse_core_gene_list(self.core_gene_list.data, self.core_genes)
            for gene in self.core_genes:
                if gene.id not in self.gene_list.data:
                    errors.append('Core gene {0} not found in gene list.'.format(gene.id))
            if errors:
                self.core_gene_list.errors.extend(errors)

        if self.gene_list.errors or self.core_gene_list.errors:
            return False

        return True


class PanelEditForm(FlaskForm):
    """Panel edit form."""
    disease_description_eng = StringField('Disease description', validators=[validators.InputRequired()])
    disease_description_nl = StringField('Ziekteomschrijving', validators=[validators.InputRequired()])
    patientfolder_alissa = StringField('Alissa', validators=[validators.InputRequired()])
    clinic_contact = StringField('Clinic contact(s)', validators=[validators.InputRequired()])
    staff_member = StringField('Staff member', validators=[validators.InputRequired()])
    comments = TextAreaField('Comments', description="Provide a short description.", validators=[validators.InputRequired()])


class PanelVersionEditForm(FlaskForm):
    """PanelVersion edit form."""

    comments = TextAreaField('Comments', description="Provide a short description.", validators=[validators.InputRequired()])
    active = BooleanField('Active')
    validated = BooleanField('Validated')
    coverage_requirement_15 = FloatField('Minimal % 15x')
    core_gene_list = TextAreaField('Core gene list', description="List of core genes seperated by newline, space, ',' or ';'.")

    core_genes = []

    def validate(self):
        """Extra validation, used to validate core gene list."""
        self.core_genes = []  # Reset core_genes on validation

        if not FlaskForm.validate(self):
            return False

        if self.core_gene_list.data:
            # Parse gene_list
            errors, self.core_genes = parse_core_gene_list(self.core_gene_list.data, self.core_genes)
            if errors:
                self.core_gene_list.errors.extend(errors)
                return False

        return True


class CustomPanelValidateForm(FlaskForm):
    """Custom Panel set validation status form."""

    confirm = BooleanField('Confirm', validators=[validators.InputRequired()])


class SampleSetPanelGeneForm(FlaskForm):
    """SampleSet Form to query a specific panel or gene."""
    sample_set = QuerySelectField(
        'Sample set',
        query_factory=active_sample_sets,
        allow_blank=True,
        blank_text='None',
        validators=[validators.InputRequired()]
    )
    panel = QuerySelectField('Panel', query_factory=all_panels, allow_blank=True, blank_text='None')
    gene = StringField('Gene')

    gene_id = ''

    def validate(self):
        """Extra validation to parse panel / gene selection"""
        self.gene_id = ''
        valid_form = True

        if not FlaskForm.validate(self):
            valid_form = False

        if not self.sample_set.data:
            message = 'Select a sample_set'
            self.sample_set.errors.append(message)
            valid_form = False

        if (self.panel.data and self.gene.data) or (not self.panel.data and not self.gene.data):
            message = 'Select a panel or gene.'
            self.panel.errors.append(message)
            self.gene.errors.append(message)
            valid_form = False
        elif self.gene.data:
            gene, error = get_gene(self.gene.data)
            if error:
                self.gene.errors.append(error)
            else:
                self.gene_id = gene.id

        return valid_form
