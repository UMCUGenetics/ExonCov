"""
ExonCov API routes.
Currently only used to implement api calls for select2 forms (ajax).
"""
from flask import request, jsonify
from flask_security import login_required
from sqlalchemy.orm import joinedload
from .models import (
    Sample, SampleProject, SampleSet, SequencingRun, PanelVersion, Panel, CustomPanel, Gene, Transcript,
    TranscriptMeasurement, panels_transcripts
)

from . import app, db
from .auth_middleware import token_required
from .models import Sample
from .utils import weighted_average


@app.route('/api/sample')
@login_required
def api_samples():
    search_term = request.args.get('term')

    samples = (
        Sample.query
        .filter(Sample.name.like('%{0}%'.format(search_term)))
        .order_by(Sample.import_date.desc())
        .order_by(Sample.name.asc())
        .all()
    )

    result = {'results': [{'id': sample.id, 'text': str(sample)} for sample in samples]}
    return jsonify(result)


@app.route('/api/protected-by-token')
@token_required
def protected_api():
    return "success"


@app.route('/api/sample/<int:id>', methods=['GET'])
@token_required
def sampleAPI(id):
    """Sample API"""

    # Query Sample and panels
    sample = (
        Sample.query
        .options(joinedload('sequencing_runs'))
        .options(joinedload('project'))
        .options(joinedload('custom_panels'))
        .get_or_404(id)
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

    results = {"results": {
            "sample": str(sample),
            "panels": list(list(panels[panel] for panel in panels)),
            "measurement_types": list(measurement_types)
            }
        }
    return jsonify(results)