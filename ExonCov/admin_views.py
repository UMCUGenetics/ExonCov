"""ExonCov admin views."""
from flask import redirect, abort, url_for, request
from flask_admin.contrib.sqla import ModelView
from flask_security import current_user

from . import db, admin
import models


class CustomModelView(ModelView):
    """Create customized default model view class."""

    can_delete = False

    # Required for flask-login implementation -> depends on authorization method
    def is_accessible(self):
        """Check whether user has acces to admin panel."""
        if current_user.is_authenticated and current_user.has_role('site_admin'):
            return True
        else:
            return False

    def _handle_view(self, name, **kwargs):
        """Redirect users when a view is not accessible."""
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class PanelAdminView(CustomModelView):
    """Panel admin view."""
    column_list = ['name', 'versions', 'disease_description_eng', 'clinical_geneticist', 'staff_member', 'comments']
    column_searchable_list = ['name']

    form_columns = [
        'name', 'disease_description_nl', 'disease_description_eng', 'comments', 'patientfolder_alissa',
        'clinical_geneticist', 'staff_member'
    ]


class PanelVersionAdminView(CustomModelView):
    """Panel version admin view."""
    column_searchable_list = ['panel_name']

    form_columns = [
        'panel', 'version_year', 'version_revision', 'comments', 'coverage_requirement_15', 'active', 'validated',
        'transcripts'
    ]
    form_ajax_refs = {
        'transcripts': {
            'fields': ['name', 'gene_id'],
            'page_size': 10
        }
    }


class CustomPanelAdminView(CustomModelView):
    """Custom panel admin view."""
    column_list = ['id', 'created_by', 'date', 'research_number', 'comments', 'validated', 'validated_by', 'validated_date']
    column_searchable_list = ['id', 'comments', 'research_number']

    form_columns = [
        'created_by', 'date', 'research_number', 'comments', 'validated', 'validated_by', 'validated_date',
        'samples', 'transcripts'
    ]

    form_ajax_refs = {
        'transcripts': {
            'fields': ['name', 'gene_id'],
            'page_size': 10
        },
        'samples': {
            'fields': ['name'],
            'page_size': 10
        }
    }


class GeneAdminView(CustomModelView):
    """Gene admin view."""
    column_list = ['id', 'default_transcript']
    column_sortable_list = ['id']
    column_searchable_list = ['id']

    form_columns = ['id', 'transcripts', 'default_transcript']
    form_ajax_refs = {
        'transcripts': {
            'fields': ['name'],
            'page_size': 10
        },
        'default_transcript': {
            'fields': ['name'],
            'page_size': 10
        }
    }


class TranscriptAdminView(CustomModelView):
    """Transcript admin view."""
    column_list = ['name', 'chr', 'start', 'end', 'gene']
    column_sortable_list = ['name', 'chr', 'start', 'end']
    column_searchable_list = ['name', 'gene_id']
    column_filters = ['chr', 'start', 'end', 'gene_id']

    form_columns = ['name', 'gene', 'exons', 'chr', 'start', 'end']
    form_ajax_refs = {
        'gene': {
            'fields': ['id'],
            'page_size': 10
        },
        'exons': {
            'fields': ['id'],
            'page_size': 10
        }
    }


class ExonAdminView(CustomModelView):
    """Exon admin view."""
    column_list = ['chr', 'start', 'end']
    column_sortable_list = ['chr', 'start', 'end']
    column_filters = ['chr', 'start', 'end']

    form_columns = ['chr', 'start', 'end']


class SampleAdminView(CustomModelView):
    """Sample admin view."""
    column_list = ['name', 'type', 'project', 'sequencing_runs', 'import_date']
    column_sortable_list = ['name', 'import_date']
    column_searchable_list = ['name']

    form_columns = [
        'name', 'type', 'project', 'sequencing_runs', 'import_date', 'file_name', 'import_command',
        'exon_measurement_file'
    ]
    form_ajax_refs = {
        'project': {
            'fields': ['name'],
            'page_size': 10
        },
        'sequencing_runs': {
            'fields': ['name'],
            'page_size': 10
        },
    }


class SampleProjectAdminView(CustomModelView):
    """SequencingRun admin view."""
    column_list = ['name']
    column_searchable_list = ['name']

    form_columns = ['name']


class SampleSetAdminView(CustomModelView):
    """Sample set admin view."""
    column_list = ['name', 'date']

    form_columns = ['name', 'date', 'description',  'active', 'samples']
    form_ajax_refs = {
        'samples': {
            'fields': ['name'],
            'page_size': 10
        },
    }


class SequencingRunAdminView(CustomModelView):
    """SequencingRun admin view."""
    column_list = ['name', 'platform_unit']
    column_searchable_list = ['name', 'platform_unit']

    form_columns = ['name', 'platform_unit']


class UserAdminView(CustomModelView):
    """User admin model."""

    can_create = False

    column_list = ('first_name', 'last_name', 'email', 'roles', 'active')
    column_searchable_list = ['first_name', 'last_name', 'email']

    form_columns = ('first_name', 'last_name', 'email', 'roles', 'active', 'password')


class EventLogAdminView(CustomModelView):
    """EventLog admin model."""
    column_filters = ['table', 'action', 'modified_on']
    column_searchable_list = ['data']

    can_create = False
    can_edit = False
    can_view_details = True


# Link view classes and models
admin.add_view(PanelAdminView(models.Panel, db.session))
admin.add_view(PanelVersionAdminView(models.PanelVersion, db.session))
admin.add_view(CustomPanelAdminView(models.CustomPanel, db.session))

admin.add_view(SampleAdminView(models.Sample, db.session))
admin.add_view(SampleProjectAdminView(models.SampleProject, db.session))
admin.add_view(SampleSetAdminView(models.SampleSet, db.session))
admin.add_view(SequencingRunAdminView(models.SequencingRun, db.session))

admin.add_view(GeneAdminView(models.Gene, db.session))
admin.add_view(TranscriptAdminView(models.Transcript, db.session))
admin.add_view(ExonAdminView(models.Exon, db.session))

admin.add_view(UserAdminView(models.User, db.session))
admin.add_view(CustomModelView(models.Role, db.session))
admin.add_view(EventLogAdminView(models.EventLog, db.session))
