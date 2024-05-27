from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_

from . import db
from .models import (
    Sample, SequencingRun, PanelVersion, Transcript, TranscriptMeasurement,
    panels_transcripts
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

    if not sample:
        return None
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


def get_sample_by_like_sample_name_or_run_id(sample_name, run_id):
    samples = (
        Sample.query
        .order_by(Sample.import_date.desc())
        .order_by(Sample.name.asc())
        .options(joinedload('sequencing_runs'))
        .options(joinedload('project'))
    )
    samples = samples.join(SequencingRun, Sample.sequencing_runs).filter(
        and_(Sample.name.like('%{0}%'.format(sample_name)), SequencingRun.platform_unit.like('%{0}%'.format(run_id))))
    return samples


def get_sample_by_sample_name(sample_name):
    sample = (
        Sample.query.options(joinedload('sequencing_runs')).options(joinedload('project')).filter_by(name=sample_name).first())
    return sample


def get_sample_by_like_run_id(run_id):
    samples = (
        Sample.query
        .order_by(Sample.import_date.desc())
        .order_by(Sample.name.asc())
        .options(joinedload('sequencing_runs'))
        .options(joinedload('project'))
    )

    samples = samples.filter(SequencingRun.id.like('%{0}%'.format(run_id)))
    return samples


def get_samples_by_like_sample_name_or_like_run_id(sample_name, run_id):
    samples = (
        Sample.query
        .order_by(Sample.import_date.desc())
        .order_by(Sample.name.asc())
        .options(joinedload('sequencing_runs'))
        .options(joinedload('project'))
    )
    samples = samples.join(SequencingRun, Sample.sequencing_runs).filter(
        or_(Sample.name.like('%{0}%'.format(sample_name)),
            SequencingRun.name.like('%{0}%'.format(run_id)),
            SequencingRun.platform_unit.like('%{0}%'.format(run_id))))

    return samples


def get_summary_by_sample_id_and_panel_id(sample_id, panel, active_panels):
    sample = Sample.query.options(joinedload('sequencing_runs')).options(joinedload('project')).get(sample_id)

    panel = (
        PanelVersion.query
        .filter_by(panel_name=panel)
        .filter_by(active=active_panels)
        .filter_by(validated=True)
        .order_by(PanelVersion.id.desc())
        .first()
    )
    panel = PanelVersion.query.options(joinedload('core_genes')).get(panel.id)

    measurement_types = {
        'measurement_mean_coverage': 'Mean coverage',
        'measurement_percentage10': '>10',
        'measurement_percentage15': '>15',
        'measurement_percentage30': '>30',
        'measurement_percentage100': '>100',
    }

    transcript_measurements = (
        db.session.query(Transcript, TranscriptMeasurement)
        .join(panels_transcripts)
        .filter(panels_transcripts.columns.panel_id == panel.id)
        .join(TranscriptMeasurement)
        .filter_by(sample_id=sample.id)
        .options(joinedload(Transcript.exons, innerjoin=True))
        .options(joinedload(Transcript.gene))
        .order_by(TranscriptMeasurement.measurement_percentage15.asc())
        .all()
    )

    # Setup panel summary
    panel_summary = {
        'measurement_percentage15': weighted_average(
            values=[tm[1].measurement_percentage15 for tm in transcript_measurements],
            weights=[tm[1].len for tm in transcript_measurements]
        ),
        'core_genes': [{"gene": str(tm[0].gene), "transcript_measurement": str(tm[0]),
                        "measurement_percentage15": str(tm[1].measurement_percentage15)} for tm
                       in transcript_measurements if tm[0].gene in panel.core_genes and tm[1].measurement_percentage15 < 100],
        'genes_15': [{"gene": str(tm[0].gene), "transcript_measurement": str(tm[0]),
                      "measurement_percentage15": str(tm[1].measurement_percentage15)} for tm
                     in transcript_measurements if tm[0].gene not in panel.core_genes and tm[1].measurement_percentage15 < 95]
    }
    return panel_summary


def get_qc_for_sample_and_panel(sample_id, panel, active_panels):
    """
    Method to get the QC values based on a sample ID and a panel name

    Args:
        sample_id (int): ID of the sample
        panel (str): panel name to lookup
        active_panels (bool): Boolean to set to include only active panels

    Returns:
        Dictionary of QC values for the given sample and panel
    """
    # Query database
    sample = Sample.query.get(sample_id)
    print(f"sample: {sample}")
    panel = (
        PanelVersion.query
        .filter_by(panel_name=panel)
        .filter_by(active=active_panels)
        .filter_by(validated=True)
        .order_by(PanelVersion.id.desc())
        .first()
    )
    print(f"panel: {panel}")

    if sample and panel:
        transcript_measurements = (
            db.session.query(Transcript, TranscriptMeasurement)
            .join(panels_transcripts)
            .filter(panels_transcripts.columns.panel_id == panel.id)
            .join(TranscriptMeasurement)
            .filter_by(sample_id=sample.id)
            .options(joinedload(Transcript.exons, innerjoin=True))
            .options(joinedload(Transcript.gene))
            .order_by(TranscriptMeasurement.measurement_percentage15.asc())
            .all()
        )

        # Calculate average panel 15X coverage and compare with coverage_requirement_15
        panel_qc = False
        panel_measurement_percentage15_avg = weighted_average(
            values=[tm[1].measurement_percentage15 for tm in transcript_measurements],
            weights=[tm[1].len for tm in transcript_measurements]
        )
        if panel_measurement_percentage15_avg >= panel.coverage_requirement_15:
            panel_qc = True

        # Check gene 15X coverage for core genes
        core_gene_qc = True
        for transcript, transcript_measurement in transcript_measurements:
            if transcript.gene in panel.core_genes and transcript_measurement.measurement_percentage15 != 100:
                core_gene_qc = False

        return {
            'sample': sample.name,
            'panel': str(panel),
            'panel_min_15x': panel.coverage_requirement_15,
            'panel_15x': panel_measurement_percentage15_avg,
            'panel_qc': panel_qc,
            'core_gene_qc': core_gene_qc
        }
    else:
        return None


def generate_not_found_dict():
    """
    Method to generate a dictionary with a not found message

    Returns:
        Dictionary with a not found status message
    """
    return {"status": "error", "message": "Not found in database"}
