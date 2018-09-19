"""ExonCov admin views."""
from flask import redirect, abort, url_for, request
from flask_admin.contrib.sqla import ModelView
from flask_security import current_user

from . import db, admin
from .models import Exon, Transcript, Gene, Panel, PanelVersion, CustomPanel, Sample, SampleSet, SequencingRun, User, Role


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
    column_list = ['name', 'versions']
    column_searchable_list = ['name']

    form_columns = ['name']


class PanelVersionAdminView(CustomModelView):
    """Panel version admin view."""
    column_searchable_list = ['panel_name']

    form_columns = ['panel', 'version_year', 'version_revision', 'active', 'validated', 'transcripts']
    form_ajax_refs = {
        'transcripts': {
            'fields': ['name', 'gene_id'],
            'page_size': 10
        }
    }


class CustomPanelAdminView(CustomModelView):
    """Custom panel admin view."""
    column_list = ['user', 'date']

    form_columns = ['user', 'date', 'samples', 'transcripts']
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
    column_sortable_list = ['name', 'chr', 'start', 'end']  # TODO: sort by gene
    column_searchable_list = ['name', 'gene_id']
    column_filters = ['chr', 'start', 'end', 'gene_id']

    form_columns = ['name', 'gene', 'exons', 'chr', 'start', 'end']  # TODO:Automatically set chr, start, end based on exons.
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
    column_list = ['name', 'sequencing_runs', 'import_date']
    column_sortable_list = ['name', 'import_date']
    column_searchable_list = ['name']

    form_columns = ['name', 'sequencing_runs', 'import_date', 'file_name', 'import_command']
    form_ajax_refs = {
        'sequencing_runs': {
            'fields': ['name'],
            'page_size': 10
        },
    }


class SampleSetAdminView(CustomModelView):
    """Sample set admin view."""
    column_list = ['name', 'date']

    form_columns = ['name', 'date', 'description', 'samples', 'active']
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


class UserAdmin(CustomModelView):
    """User admin model."""

    can_create = False

    column_list = ('first_name', 'last_name', 'email', 'roles', 'active')

    form_columns = ('first_name', 'last_name', 'email', 'roles', 'active', 'password')


# Link view classes and models
admin.add_view(PanelAdminView(Panel, db.session))
admin.add_view(PanelVersionAdminView(PanelVersion, db.session))
admin.add_view(CustomPanelAdminView(CustomPanel, db.session))

admin.add_view(GeneAdminView(Gene, db.session))
admin.add_view(TranscriptAdminView(Transcript, db.session))
admin.add_view(ExonAdminView(Exon, db.session))

admin.add_view(SampleAdminView(Sample, db.session))
admin.add_view(SampleSetAdminView(SampleSet, db.session))
admin.add_view(SequencingRunAdminView(SequencingRun, db.session))

admin.add_view(UserAdmin(User, db.session))
admin.add_view(CustomModelView(Role, db.session))
