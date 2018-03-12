"""ExonCov views."""

from collections import OrderedDict

from flask import render_template, request

from ExonCov import app, db
from .models import Sample, Panel, Gene, Transcript, Exon, ExonMeasurement, TranscriptMeasurement, panels_transcripts, exons_transcripts
from .forms import CustomPanelForm


@app.route('/')
@app.route('/sample')
def samples():
    """Sample overview page."""
    samples = Sample.query.all()
    return render_template('samples.html', samples=samples)


@app.route('/sample/<int:id>')
def sample(id):
    """Sample page."""
    sample = Sample.query.get(id)
    measurement_types = ['measurement_mean_coverage', 'measurement_percentage15', 'measurement_percentage30']
    query = db.session.query(Panel.name, TranscriptMeasurement).join(Transcript, Panel.transcripts).join(TranscriptMeasurement).filter_by(sample_id=sample.id).order_by(Panel.name).all()
    panels = OrderedDict()

    for panel_name, transcript_measurement in query:
        if panel_name not in panels:
            panels[panel_name] = {
                'len': transcript_measurement.len
            }
            for measurement_type in measurement_types:
                panels[panel_name][measurement_type] = transcript_measurement[measurement_type]
        else:
            for measurement_type in measurement_types:
                panels[panel_name][measurement_type] = ((panels[panel_name]['len'] * panels[panel_name][measurement_type]) + (transcript_measurement.len * transcript_measurement[measurement_type])) / (panels[panel_name]['len'] + transcript_measurement.len)
            panels[panel_name]['len'] += transcript_measurement.len
    return render_template('sample.html', sample=sample, panels=panels, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/panel/<string:panel_name>')
def sample_panel(sample_id, panel_name):
    """Sample panel page."""
    sample = Sample.query.get(sample_id)
    panel = Panel.query.filter_by(name=panel_name).first()

    measurement_types = ['measurement_mean_coverage', 'measurement_percentage15', 'measurement_percentage30']
    transcript_measurements = db.session.query(Transcript, TranscriptMeasurement).join(panels_transcripts).filter(panels_transcripts.columns.panel_id == panel.id).join(TranscriptMeasurement).filter_by(sample_id=sample.id).all()
    return render_template('sample_panel.html', sample=sample, panel=panel, transcript_measurements=transcript_measurements, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/transcript/<string:transcript_name>')
def sample_transcript(sample_id, transcript_name):
    """Sample transcript page."""
    sample = Sample.query.get(sample_id)
    transcript = Transcript.query.filter_by(name=transcript_name).first()

    measurement_types = ['measurement_mean_coverage', 'measurement_percentage15', 'measurement_percentage30']
    exon_measurements = db.session.query(Exon, ExonMeasurement).join(exons_transcripts).filter(exons_transcripts.columns.transcript_id == transcript.id).join(ExonMeasurement).filter_by(sample_id=sample.id).order_by(Exon.start).all()

    return render_template('sample_transcript.html', sample=sample, transcript=transcript, exon_measurements=exon_measurements, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/gene/<string:gene_id>')
def sample_gene(sample_id, gene_id):
    """Sample gene page."""
    sample = Sample.query.get(sample_id)
    gene = Gene.query.get(gene_id)

    measurement_types = ['measurement_mean_coverage', 'measurement_percentage15', 'measurement_percentage30']
    transcript_measurements = db.session.query(Transcript, TranscriptMeasurement).filter(Transcript.gene_id == gene.id).join(TranscriptMeasurement).filter_by(sample_id=sample.id).all()

    return render_template('sample_gene.html', sample=sample, gene=gene, transcript_measurements=transcript_measurements, measurement_types=measurement_types)


@app.route('/panel')
def panels():
    """Panel overview page."""
    panels = Panel.query.all()
    return render_template('panels.html', panels=panels)


@app.route('/panel/<int:id>')
def panel(id):
    """Panel page."""
    panel = Panel.query.get(id)
    return render_template('panel.html', panel=panel)


@app.route('/panel/custom', methods=['GET'])
def custom_panel():
    """Custom panel page."""
    custom_panel_form = CustomPanelForm(request.args, meta={'csrf': False})
    samples = []
    measurement_type = []
    sample_measurements = {}
    transcript_measurements = {}

    if request.args and custom_panel_form.validate():
        samples = custom_panel_form.data['samples']
        measurement_type = [custom_panel_form.data['measurement_type'], dict(custom_panel_form.measurement_type.choices).get(custom_panel_form.data['measurement_type'])]
        transcript_ids = custom_panel_form.transcript_ids
        sample_ids = [sample.id for sample in samples]

        query = db.session.query(TranscriptMeasurement).filter(TranscriptMeasurement.sample_id.in_(sample_ids)).filter(TranscriptMeasurement.transcript_id.in_(transcript_ids)).all()
        for transcript_measurement in query:
            sample = transcript_measurement.sample  # Add join?
            transcript = transcript_measurement.transcript  # Add Join??

            # Store transcript_measurements per transcript and sample
            if transcript not in transcript_measurements:
                transcript_measurements[transcript] = {}
            transcript_measurements[transcript][sample] = transcript_measurement[measurement_type[0]]

            # Calculate weighted average per sample for entire panel
            if sample not in sample_measurements:
                sample_measurements[sample] = {
                    'len': transcript_measurement.len,
                    'measurement': transcript_measurement[measurement_type[0]]
                }
            else:
                sample_measurements[sample]['measurement'] = ((sample_measurements[sample]['len'] * sample_measurements[sample]['measurement']) + (transcript_measurement.len * transcript_measurement[measurement_type[0]])) / (sample_measurements[sample]['len'] + transcript_measurement.len)
                sample_measurements[sample]['len'] += transcript_measurement.len

    # Calculate min, mean, max
    for transcript in transcript_measurements:
        values = transcript_measurements[transcript].values()
        transcript_measurements[transcript]['min'] = min(values)
        transcript_measurements[transcript]['max'] = max(values)
        transcript_measurements[transcript]['mean'] = float(sum(values)) / len(values)

    values = [sample_measurements[sample]['measurement'] for sample in sample_measurements]
    sample_measurements['min'] = min(values)
    sample_measurements['max'] = max(values)
    sample_measurements['mean'] = float(sum(values)) / len(values)


    return render_template('custom_panel.html', form=custom_panel_form, samples=samples, measurement_type=measurement_type, transcript_measurements=transcript_measurements, sample_measurements=sample_measurements)
