import time
import datetime

from flask import render_template, request, redirect, url_for
from flask_security import login_required, roles_required
from flask_login import current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
import pysam

from . import app, db
from .models import (
    Sample, SampleProject, SampleSet, SequencingRun, PanelVersion, Panel, CustomPanel, Gene, Transcript,
    TranscriptMeasurement
)
from .forms import (
    SampleGeneForm
)
from .utils import weighted_average


def get_sample_by_id(id):
    # Query Sample and panels
    sample = (
        Sample.query
        .options(joinedload('sequencing_runs'))
        .options(joinedload('project'))
        .options(joinedload('custom_panels'))
        .get(id)
    )
    query = (
        db.session.query(PanelVersion, TranscriptMeasurement)
        .filter_by(active=True)
        .filter_by(validated=True)
        .join(Transcript, PanelVersion.transcripts)
        .join(TranscriptMeasurement)
        .filter_by(sample_id=sample.id)
        .order_by(PanelVersion.panel_name)
        .all()
    )
    measurement_types = {
        'measurement_mean_coverage': 'Mean coverage',
        'measurement_percentage10': '>10',
        'measurement_percentage15': '>15',
        'measurement_percentage30': '>30',
        'measurement_percentage100': '>100',
    }
    panels = {}

    for panel, transcript_measurement in query:
        if panel.id not in panels:
            panels[panel.id] = {
                'description': panel.panel.disease_description_nl,
                'len': transcript_measurement.len,
                'name_version': panel.name_version,
                'coverage_requirement_15': panel.coverage_requirement_15
            }
            for measurement_type in measurement_types:
                panels[panel.id][measurement_type] = transcript_measurement[measurement_type]
        else:
            for measurement_type in measurement_types:
                panels[panel.id][measurement_type] = weighted_average(
                    values=[panels[panel.id][measurement_type], transcript_measurement[measurement_type]],
                    weights=[panels[panel.id]['len'], transcript_measurement.len]
                )
            panels[panel.id]['len'] += transcript_measurement.len
    print(sample.name)
    print(sample.import_date)

    return sample
