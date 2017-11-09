"""ExonCov views."""

from flask import render_template

from ExonCov import app, db
from .models import Sample, Panel, Gene, Transcript, Exon, ExonMeasurement, panels_transcripts, exons_transcripts


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
    measurement_types = ['meanCoverage', 'percentage15', 'percentage30']
    query = db.session.query(Panel.name, Exon.len, ExonMeasurement.measurement_type, ExonMeasurement.measurement).join(Transcript, Panel.transcripts).join(Exon, Transcript.exons).join(ExonMeasurement).filter_by(sample_id=sample.id).filter(ExonMeasurement.measurement_type.in_(measurement_types)).all()

    measurements = {}

    for panel_name, exon_len, measurement_type, measurement in query:
        if panel_name not in measurements:
            measurements[panel_name] = dict((key, {'value': 0, 'len': 0}) for key in measurement_types)

        measurements[panel_name][measurement_type]['value'] = ((measurements[panel_name][measurement_type]['len'] * measurements[panel_name][measurement_type]['value']) + (exon_len * measurement)) / (measurements[panel_name][measurement_type]['len'] + exon_len)
        measurements[panel_name][measurement_type]['len'] += exon_len

    return render_template('sample.html', sample=sample, measurements=measurements, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/panel/<string:panel_name>')
def sample_panel(sample_id, panel_name):
    """Sample panel page."""
    sample = Sample.query.get(sample_id)
    panel = Panel.query.filter_by(name=panel_name).first()

    measurement_types = ['meanCoverage', 'percentage15', 'percentage30']
    query = db.session.query(Transcript.name, Transcript.gene_id, Exon.chr, Exon.start, Exon.end, ExonMeasurement.measurement_type, ExonMeasurement.measurement).join(panels_transcripts).filter(panels_transcripts.columns.panel_id == panel.id).join(Exon, Transcript.exons).join(ExonMeasurement).filter_by(sample_id=sample.id).filter(ExonMeasurement.measurement_type.in_(measurement_types)).all()
    measurements = {}

    for transcript_name, gene_id, exon_chr, exon_start, exon_end, measurement_type, measurement in query:
        exon_len = exon_end - exon_start
        if transcript_name not in measurements:
            measurements[transcript_name] = dict((key, {'value': 0, 'len': 0, 'chr': exon_chr, 'start': exon_start, 'end': exon_end, 'exon_count': 0, 'gene': gene_id}) for key in measurement_types)
        measurements[transcript_name][measurement_type]['value'] = ((measurements[transcript_name][measurement_type]['len'] * measurements[transcript_name][measurement_type]['value']) + (exon_len * measurement)) / (measurements[transcript_name][measurement_type]['len'] + exon_len)
        measurements[transcript_name][measurement_type]['len'] += exon_len
        measurements[transcript_name][measurement_type]['exon_count'] += 1

        if measurements[transcript_name][measurement_type]['start'] > exon_start:
            measurements[transcript_name][measurement_type]['start'] = exon_start
        if measurements[transcript_name][measurement_type]['end'] < exon_end:
            measurements[transcript_name][measurement_type]['end'] = exon_end

    return render_template('sample_panel.html', sample=sample, panel=panel, measurements=measurements, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/transcript/<string:transcript_name>')
def sample_transcript(sample_id, transcript_name):
    """Sample transcript page."""
    sample = Sample.query.get(sample_id)
    transcript = Transcript.query.filter_by(name=transcript_name).first()

    measurement_types = ['meanCoverage', 'percentage15', 'percentage30']
    query = db.session.query(Exon.id, Exon.chr, Exon.start, Exon.end, ExonMeasurement.measurement_type, ExonMeasurement.measurement).join(exons_transcripts).filter(exons_transcripts.columns.transcript_id == transcript.id).join(ExonMeasurement).filter_by(sample_id=sample.id).filter(ExonMeasurement.measurement_type.in_(measurement_types)).all()
    exons = {}

    for exon_id, exon_chr, exon_start, exon_end, measurement_type, measurement in query:
        if exon_id not in exons:
            exons[exon_id] = {
                'chr': exon_chr,
                'start': exon_start,
                'end': exon_end
            }
        exons[exon_id][measurement_type] = measurement

    return render_template('sample_transcript.html', sample=sample, transcript=transcript, exons=exons, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/gene/<string:gene_id>')
def sample_gene(sample_id, gene_id):
    """Sample gene page."""
    sample = Sample.query.get(sample_id)
    gene = Gene.query.get(gene_id)

    measurement_types = ['meanCoverage', 'percentage15', 'percentage30']
    query = db.session.query(Transcript.name, Transcript.gene_id, Exon.chr, Exon.start, Exon.end, ExonMeasurement.measurement_type, ExonMeasurement.measurement).filter(Transcript.gene_id == gene.id).join(Exon, Transcript.exons).join(ExonMeasurement).filter_by(sample_id=sample.id).filter(ExonMeasurement.measurement_type.in_(measurement_types)).all()

    measurements = {}

    for transcript_name, gene_id, exon_chr, exon_start, exon_end, measurement_type, measurement in query:
        exon_len = exon_end - exon_start
        if transcript_name not in measurements:
            measurements[transcript_name] = dict((key, {'value': 0, 'len': 0, 'chr': exon_chr, 'start': exon_start, 'end': exon_end, 'exon_count': 0}) for key in measurement_types)
        measurements[transcript_name][measurement_type]['value'] = ((measurements[transcript_name][measurement_type]['len'] * measurements[transcript_name][measurement_type]['value']) + (exon_len * measurement)) / (measurements[transcript_name][measurement_type]['len'] + exon_len)
        measurements[transcript_name][measurement_type]['len'] += exon_len
        measurements[transcript_name][measurement_type]['exon_count'] += 1

        if measurements[transcript_name][measurement_type]['start'] > exon_start:
            measurements[transcript_name][measurement_type]['start'] = exon_start
        if measurements[transcript_name][measurement_type]['end'] < exon_end:
            measurements[transcript_name][measurement_type]['end'] = exon_end

    return render_template('sample_gene.html', sample=sample, gene=gene, measurements=measurements, measurement_types=measurement_types)
