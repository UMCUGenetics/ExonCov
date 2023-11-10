"""ExonCov admin views."""
import datetime

from flask import redirect, abort, url_for, request, Markup
from flask_admin.contrib.sqla import ModelView
from flask_security import current_user
import jwt
import config

from . import db, admin
from ExonCov import models


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
    column_list = ['name', 'versions', 'disease_description_eng', 'clinic_contact', 'staff_member', 'comments']
    column_searchable_list = ['name']

    form_columns = [
        'name', 'disease_description_nl', 'disease_description_eng', 'comments', 'patientfolder_alissa',
        'clinic_contact', 'staff_member'
    ]


class PanelVersionAdminView(CustomModelView):
    """Panel version admin view."""
    column_searchable_list = ['panel_name']

    form_columns = [
        'panel', 'version_year', 'version_revision', 'comments', 'coverage_requirement_15', 'created_date',
        'active', 'validated', 'release_date', 'transcripts', 'core_genes'
    ]
    form_ajax_refs = {
        'transcripts': {
            'fields': ['name', 'gene_id'],
            'page_size': 10
        },
        'core_genes': {
            'fields': ['id'],
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
    column_list = ['name', 'type']
    column_searchable_list = ['name', 'type']

    form_columns = ['name', 'type']


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


class APITokensAdminView(CustomModelView):
    can_edit = False
    can_create = True
    can_delete = True
    can_view_details = True
    details_modal = True
    create_modal = True
    column_labels = dict(application='Application name', token="API Token")
    # column_formatters = dict(token=lambda a : a[ 0 : 10 ])

    column_formatters_detail = {
        'token': lambda v, c, m, p: Markup(f'{m.token}<br><br><div class="alert alert-warning" role="alert"><span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span><span class="sr-only">Error:</span>&nbsp;Keep this token secret and do not use it for other applications</div>')
    }
    column_formatters = {
        'token': lambda v, c, m, p: Markup(
            f'{m.token[:3]}...{m.token[-4:]} <a href="/admin/apitokens/details/?id={m.id}&url=%2Fadmin%2Fapitokens%2F%3Fsort%3D0&modal=True" data-target="#fa_modal_window" data-toggle="modal">see full token')
    }

    column_list = ["application", "token", "modified_on"]
    form_columns = ["application"]

    def on_model_change(self, form, model, is_created):
        # Perform actions when a model is changed (created or modified)
        if is_created:
            # Set the created_at column to the current time when a new record is created
            model.created_at = datetime.datetime.now()
            model.user_id = 54
            model.token = jwt.encode({"app": model.application, "iat":model.created_at}, config.JWT_SECRET, algorithm="HS256")


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

admin.add_view(UserAdminView(models.User, db.session, category="Authentication "))
admin.add_view(CustomModelView(models.Role, db.session, category="Authentication "))
admin.add_view(APITokensAdminView(models.APITokens, db.session, name='API Tokens', category="Authentication ", endpoint="apitokens"))
admin.add_view(EventLogAdminView(models.EventLog, db.session))