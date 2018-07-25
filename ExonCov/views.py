"""ExonCov views."""

from collections import OrderedDict
import time

from flask import render_template, request, redirect, url_for
from flask_security import login_required, roles_required
from sqlalchemy.orm import joinedload

from ExonCov import app, db
from .models import Sample, SequencingRun, PanelVersion, Panel, Gene, Transcript, Exon, ExonMeasurement, TranscriptMeasurement, panels_transcripts, exons_transcripts
from .forms import CustomPanelForm, SampleForm, CreatePanelForm, UpdatePanelForm


@app.route('/')
@app.route('/sample')
@login_required
def samples():
    """Sample overview page."""
    sample_form = SampleForm(request.args, meta={'csrf': False})
    page = request.args.get('page', default=1, type=int)
    sample = request.args.get('sample')
    run = request.args.get('run')
    samples_per_page = 5

    if (sample or run) and sample_form.validate():
        samples = Sample.query
        if sample:
            samples = samples.filter(Sample.name.like('%{0}%'.format(sample)))
        if run:
            samples = samples.join(SequencingRun).filter(SequencingRun.name.like('%{0}%'.format(run)))
        samples = samples.paginate(page=page, per_page=samples_per_page)
    else:
        samples = Sample.query.paginate(page=page, per_page=samples_per_page)

    return render_template('samples.html', form=sample_form, samples=samples)


@app.route('/sample/<int:id>')
@login_required
def sample(id):
    """Sample page."""
    sample = Sample.query.get(id)
    measurement_types = {
        'measurement_mean_coverage': 'Mean coverage',
        'measurement_percentage10': '>10',
        'measurement_percentage15': '>15',
        'measurement_percentage30': '>30'
    }
    query = db.session.query(PanelVersion, TranscriptMeasurement).join(Transcript, PanelVersion.transcripts).join(TranscriptMeasurement).filter_by(sample_id=sample.id).order_by(PanelVersion.panel_name).all()
    panels = OrderedDict()

    for panel, transcript_measurement in query:
        if panel.id not in panels:
            panels[panel.id] = {
                'len': transcript_measurement.len,
                'name_version': panel.name_version,
            }
            for measurement_type in measurement_types:
                panels[panel.id][measurement_type] = transcript_measurement[measurement_type]
        else:
            for measurement_type in measurement_types:
                panels[panel.id][measurement_type] = ((panels[panel.id]['len'] * panels[panel.id][measurement_type]) + (transcript_measurement.len * transcript_measurement[measurement_type])) / (panels[panel.id]['len'] + transcript_measurement.len)
            panels[panel.id]['len'] += transcript_measurement.len
    return render_template('sample.html', sample=sample, panels=panels, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/panel/<int:panel_id>')
@login_required
def sample_panel(sample_id, panel_id):
    """Sample panel page."""
    sample = Sample.query.get(sample_id)
    panel = PanelVersion.query.get(panel_id)

    measurement_types = {
        'measurement_mean_coverage': 'Mean coverage',
        'measurement_percentage10': '>10',
        'measurement_percentage15': '>15',
        'measurement_percentage30': '>30'
    }
    transcript_measurements = db.session.query(Transcript, TranscriptMeasurement).join(panels_transcripts).filter(panels_transcripts.columns.panel_id == panel.id).join(TranscriptMeasurement).filter_by(sample_id=sample.id).options(joinedload(Transcript.exons, innerjoin=True)).all()
    return render_template('sample_panel.html', sample=sample, panel=panel, transcript_measurements=transcript_measurements, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/transcript/<string:transcript_name>')
@login_required
def sample_transcript(sample_id, transcript_name):
    """Sample transcript page."""
    sample = Sample.query.get(sample_id)
    transcript = Transcript.query.filter_by(name=transcript_name).first()

    measurement_types = {
        'measurement_mean_coverage': 'Mean coverage',
        'measurement_percentage10': '>10',
        'measurement_percentage15': '>15',
        'measurement_percentage30': '>30'
    }
    exon_measurements = db.session.query(Exon, ExonMeasurement).join(exons_transcripts).filter(exons_transcripts.columns.transcript_id == transcript.id).join(ExonMeasurement).filter_by(sample_id=sample.id).order_by(Exon.start).all()

    return render_template('sample_transcript.html', sample=sample, transcript=transcript, exon_measurements=exon_measurements, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/gene/<string:gene_id>')
@login_required
def sample_gene(sample_id, gene_id):
    """Sample gene page."""
    sample = Sample.query.get(sample_id)
    gene = Gene.query.get(gene_id)

    measurement_types = {
        'measurement_mean_coverage': 'Mean coverage',
        'measurement_percentage10': '>10',
        'measurement_percentage15': '>15',
        'measurement_percentage30': '>30'
    }
    transcript_measurements = db.session.query(Transcript, TranscriptMeasurement).filter(Transcript.gene_id == gene.id).join(TranscriptMeasurement).filter_by(sample_id=sample.id).options(joinedload(Transcript.exons, innerjoin=True)).all()

    return render_template('sample_gene.html', sample=sample, gene=gene, transcript_measurements=transcript_measurements, measurement_types=measurement_types)


@app.route('/panel')
@login_required
def panels():
    """Panel overview page."""
    panels = PanelVersion.query.options(joinedload('transcripts')).all()
    return render_template('panels.html', panels=panels)


@app.route('/panel/<int:id>')
@login_required
def panel(id):
    """Panel page."""
    panel = PanelVersion.query.get(id)
    return render_template('panel.html', panel=panel)


@app.route('/panel/<int:id>/update', methods=['GET', 'POST'])
@login_required
@roles_required('panel_admin')
def panel_update(id):
    """Panel page."""
    panel = PanelVersion.query.get(id)
    genes = '\n'.join([transcript.gene_id for transcript in panel.transcripts])
    update_panel_form = UpdatePanelForm(gene_list=genes)

    if update_panel_form.validate_on_submit():
        transcripts = update_panel_form.transcripts

        if sorted(transcripts) == sorted(panel.transcripts):
            update_panel_form.gene_list.errors.append('No changes.')
        else:
            # Determine version number
            year = int(time.strftime('%y'))
            if panel.version_year == year:
                revision = panel.version_revision + 1
            else:
                revision = 1

            new_panel_version = PanelVersion(panel_name=panel.panel_name, version_year=year, version_revision=revision, active=True, transcripts=transcripts)
            db.session.add(new_panel_version)
            db.session.commit()
            return redirect(url_for('panel', id=new_panel_version.id))
    return render_template('panel_update.html', form=update_panel_form, panel=panel)


@app.route('/panel/new', methods=['GET', 'POST'])
@login_required
@roles_required('panel_admin')
def panel_new():
    """Create new panel page."""
    new_panel_form = CreatePanelForm()

    if new_panel_form.validate_on_submit():
        panel_name = new_panel_form.data['name']
        transcripts = new_panel_form.transcripts

        new_panel = Panel(name=panel_name)
        new_panel_version = PanelVersion(panel_name=panel_name, version_year=time.strftime('%y'), version_revision=1, active=True, transcripts=transcripts)

        db.session.add(new_panel)
        db.session.add(new_panel_version)
        db.session.commit()
        return redirect(url_for('panel', id=new_panel_version.id))
    return render_template('panel_new.html', form=new_panel_form)


@app.route('/panel/custom', methods=['GET'])
@login_required
def custom_panel():
    """Custom panel page."""
    custom_panel_form = CustomPanelForm(request.args, meta={'csrf': False})
    samples = []
    sample_ids = []
    measurement_type = []
    panel_measurements = {}
    transcript_measurements = {}

    if request.args and custom_panel_form.validate():
        samples = custom_panel_form.data['samples']
        measurement_type = [custom_panel_form.data['measurement_type'], dict(custom_panel_form.measurement_type.choices).get(custom_panel_form.data['measurement_type'])]
        transcript_ids = custom_panel_form.transcript_ids
        sample_ids = [sample.id for sample in samples]

        query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).filter(TranscriptMeasurement.transcript_id.in_(transcript_ids)).options(joinedload('transcript')).all()
        for transcript_measurement in query:
            sample = transcript_measurement.sample
            transcript = transcript_measurement.transcript

            # Store transcript_measurements per transcript and sample
            if transcript not in transcript_measurements:
                transcript_measurements[transcript] = {}
            transcript_measurements[transcript][sample] = transcript_measurement[measurement_type[0]]

            # Calculate weighted average per sample for entire panel
            if sample not in panel_measurements:
                panel_measurements[sample] = {
                    'len': transcript_measurement.len,
                    'measurement': transcript_measurement[measurement_type[0]]
                }
            else:
                panel_measurements[sample]['measurement'] = ((panel_measurements[sample]['len'] * panel_measurements[sample]['measurement']) + (transcript_measurement.len * transcript_measurement[measurement_type[0]])) / (panel_measurements[sample]['len'] + transcript_measurement.len)
                panel_measurements[sample]['len'] += transcript_measurement.len

        # Calculate min, mean, max
        for transcript in transcript_measurements:
            values = transcript_measurements[transcript].values()
            transcript_measurements[transcript]['min'] = min(values)
            transcript_measurements[transcript]['max'] = max(values)
            transcript_measurements[transcript]['mean'] = float(sum(values)) / len(values)

        values = [panel_measurements[sample]['measurement'] for sample in panel_measurements]
        panel_measurements['min'] = min(values)
        panel_measurements['max'] = max(values)
        panel_measurements['mean'] = float(sum(values)) / len(values)

    return render_template('custom_panel.html', form=custom_panel_form, samples=samples, sample_ids=sample_ids, measurement_type=measurement_type, transcript_measurements=transcript_measurements, panel_measurements=panel_measurements)


@app.route('/panel/custom/transcript/<string:transcript_name>', methods=['GET'])
@login_required
def custom_panel_transcript(transcript_name):
    """Custom panel transcript page."""
    transcript = Transcript.query.filter_by(name=transcript_name).first()
    sample_ids = request.args.getlist('sample')
    samples = []
    measurement_type = request.args['measurement_type']
    exon_measurements = OrderedDict()
    transcript_measurements = {}

    if sample_ids and measurement_type:
        # Get transcript measurements
        query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).filter_by(transcript_id=transcript.id).options(joinedload('sample')).all()
        for transcript_measurement in query:
            sample = transcript_measurement.sample
            transcript_measurements[sample] = transcript_measurement[measurement_type]

            # Store sample
            if sample not in samples:
                samples.append(sample)

        # Get exon measurements
        query = db.session.query(ExonMeasurement).join(Exon).join(exons_transcripts).filter(exons_transcripts.columns.transcript_id == transcript.id).filter(ExonMeasurement.sample_id.in_(sample_ids)).order_by(Exon.start).options(joinedload(ExonMeasurement.exon, innerjoin=True)).all()
        for exon_measurement in query:
            sample = exon_measurement.sample
            exon = exon_measurement.exon

            # Store exon_measurement per exon and sample
            if exon not in exon_measurements:
                exon_measurements[exon] = {}
            exon_measurements[exon][sample] = exon_measurement[measurement_type]

        # Calculate min, mean, max
        values = transcript_measurements.values()
        transcript_measurements['min'] = min(values)
        transcript_measurements['max'] = max(values)
        transcript_measurements['mean'] = float(sum(values)) / len(values)

        for exon in exon_measurements:
            values = exon_measurements[exon].values()
            exon_measurements[exon]['min'] = min(values)
            exon_measurements[exon]['max'] = max(values)
            exon_measurements[exon]['mean'] = float(sum(values)) / len(values)

    return render_template('custom_panel_transcript.html', transcript=transcript, samples=samples, transcript_measurements=transcript_measurements, exon_measurements=exon_measurements)


@app.route('/panel/custom/gene/<string:gene_id>', methods=['GET'])
@login_required
def custom_panel_gene(gene_id):
    """Custom panel gene page."""
    gene = Gene.query.get(gene_id)
    sample_ids = request.args.getlist('sample')
    samples = []
    measurement_type = request.args['measurement_type']
    transcript_measurements = {}

    if sample_ids and measurement_type:
        query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).join(Transcript).filter_by(gene_id=gene_id).options(joinedload('sample')).options(joinedload('transcript')).all()
        for transcript_measurement in query:
            sample = transcript_measurement.sample
            transcript = transcript_measurement.transcript

            if transcript not in transcript_measurements:
                transcript_measurements[transcript] = {}
            transcript_measurements[transcript][sample] = transcript_measurement[measurement_type]

            if sample not in samples:
                samples.append(sample)

        for transcript in transcript_measurements:
            values = transcript_measurements[transcript].values()
            transcript_measurements[transcript]['min'] = min(values)
            transcript_measurements[transcript]['max'] = max(values)
            transcript_measurements[transcript]['mean'] = float(sum(values)) / len(values)

    return render_template('custom_panel_gene.html', gene=gene, samples=samples, sample_ids=sample_ids, measurement_type=measurement_type, transcript_measurements=transcript_measurements)
