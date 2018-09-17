"""ExonCov views."""

from collections import OrderedDict
import time

from flask import render_template, request, redirect, url_for
from flask_security import login_required, roles_required
from flask_login import current_user
from sqlalchemy.orm import joinedload

from ExonCov import app, db
from .models import Sample, SequencingRun, PanelVersion, Panel, CustomPanel, Gene, Transcript, Exon, ExonMeasurement, TranscriptMeasurement, panels_transcripts, exons_transcripts
from .forms import CustomPanelForm, CustomPanelNewForm, SampleForm, CreatePanelForm, UpdatePanelForm
from .utils import weighted_average


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
            samples = samples.join(SequencingRun, Sample.sequencing_runs).filter(SequencingRun.name.like('%{0}%'.format(run)))
        samples = samples.paginate(page=page, per_page=samples_per_page)
    else:
        samples = Sample.query.paginate(page=page, per_page=samples_per_page)

    return render_template('samples.html', form=sample_form, samples=samples)


@app.route('/sample/<int:id>')
@login_required
def sample(id):
    """Sample page."""
    sample = Sample.query.get_or_404(id)
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
                panels[panel.id][measurement_type] = weighted_average(
                    [panels[panel.id][measurement_type], transcript_measurement[measurement_type]],
                    [panels[panel.id]['len'], transcript_measurement.len]
                )
            panels[panel.id]['len'] += transcript_measurement.len
    return render_template('sample.html', sample=sample, panels=panels, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/panel/<int:panel_id>')
@login_required
def sample_panel(sample_id, panel_id):
    """Sample panel page."""
    sample = Sample.query.get_or_404(sample_id)
    panel = PanelVersion.query.get_or_404(panel_id)

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
    sample = Sample.query.get_or_404(sample_id)
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
    sample = Sample.query.get_or_404(sample_id)
    gene = Gene.query.get_or_404(gene_id)

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
    panels = Panel.query.options(joinedload('versions')).all()
    custom_panels = CustomPanel.query.order_by(CustomPanel.id.desc()).all()

    return render_template('panels.html', panels=panels, custom_panels=custom_panels)


@app.route('/panel/<string:name>')
@login_required
def panel(name):
    """Panel page."""
    panel = Panel.query.filter_by(name=name).options(joinedload('versions').joinedload('transcripts')).first()
    return render_template('panel.html', panel=panel)


@app.route('/panel/<string:name>/update', methods=['GET', 'POST'])
@login_required
@roles_required('panel_admin')
def panel_update(name):
    """Update panel page."""
    panel = Panel.query.filter_by(name=name).first()
    panel_last_version = panel.last_version

    genes = '\n'.join([transcript.gene_id for transcript in panel_last_version.transcripts])
    update_panel_form = UpdatePanelForm(gene_list=genes)

    if update_panel_form.validate_on_submit():
        transcripts = update_panel_form.transcripts

        # Check for panel changes
        if sorted(transcripts) == sorted(panel_last_version.transcripts):
            update_panel_form.gene_list.errors.append('No changes.')

        else:
            # Create new panel if confirmed or show confirm page.
            # Determine version number
            year = int(time.strftime('%y'))
            if panel_last_version.version_year == year:
                revision = panel_last_version.version_revision + 1
            else:
                revision = 1

            if update_panel_form.confirm.data:
                panel_new_version = PanelVersion(panel_name=panel.name, version_year=year, version_revision=revision, active=True, transcripts=transcripts)
                db.session.add(panel_new_version)
                db.session.commit()
                return redirect(url_for('panel', name=panel.name))
            else:
                return render_template('panel_update_confirm.html', form=update_panel_form, panel=panel_last_version, year=year, revision=revision)

    return render_template('panel_update.html', form=update_panel_form, panel=panel_last_version)


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
        return redirect(url_for('panel', name=new_panel.name))
    return render_template('panel_new.html', form=new_panel_form)


@app.route('/panel_version/<int:id>')
@login_required
def panel_version(id):
    """PanelVersion page."""
    panel = PanelVersion.query.options(joinedload('transcripts').joinedload('exons')).options(joinedload('transcripts').joinedload('gene')).get_or_404(id)
    return render_template('panel_version.html', panel=panel)


@app.route('/panel/custom', methods=['GET', 'POST'])
@login_required
def custom_panel_new():
    """New custom panel page."""
    # TODO: Page layout
    custom_panel_form = CustomPanelNewForm()

    if custom_panel_form.validate_on_submit():
        custom_panel = CustomPanel(
            user=current_user,
            transcripts=custom_panel_form.transcripts,
            samples=custom_panel_form.data['samples']
        )
        db.session.add(custom_panel)
        db.session.commit()
        return redirect(url_for('custom_panel', id=custom_panel.id))

    return render_template('custom_panel_new.html', form=custom_panel_form)


@app.route('/panel/custom/<int:id>', methods=['GET', 'POST'])
@login_required
def custom_panel(id):
    """Custom panel page."""
    # TODO: Page layout
    custom_panel = CustomPanel.query.options(joinedload('transcripts')).get_or_404(id)
    custom_panel_form = CustomPanelForm()

    sample_ids = [sample.id for sample in custom_panel.samples]
    transcript_ids = [transcript.id for transcript in custom_panel.transcripts]
    measurement_type = [custom_panel_form.data['measurement_type'], dict(custom_panel_form.measurement_type.choices).get(custom_panel_form.data['measurement_type'])]
    transcript_measurements = {}
    panel_measurements = {}

    query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).filter(TranscriptMeasurement.transcript_id.in_(transcript_ids)).options(joinedload('transcript').joinedload('gene')).all()

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
            panel_measurements[sample]['measurement'] = weighted_average(
                [panel_measurements[sample]['measurement'], transcript_measurement[measurement_type[0]]],
                [panel_measurements[sample]['len'], transcript_measurement.len]
            )
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

    return render_template('custom_panel.html', form=custom_panel_form, custom_panel=custom_panel, measurement_type=measurement_type, transcript_measurements=transcript_measurements, panel_measurements=panel_measurements)


@app.route('/panel/custom/<int:id>/transcript/<string:transcript_name>', methods=['GET', 'POST'])
@login_required
def custom_panel_transcript(id, transcript_name):
    """Custom panel transcript page."""
    # TODO: Page layout
    custom_panel = CustomPanel.query.options(joinedload('samples')).get_or_404(id)
    custom_panel_form = CustomPanelForm()

    sample_ids = [sample.id for sample in custom_panel.samples]
    transcript = Transcript.query.filter_by(name=transcript_name).options(joinedload('gene')).first()
    measurement_type = [custom_panel_form.data['measurement_type'], dict(custom_panel_form.measurement_type.choices).get(custom_panel_form.data['measurement_type'])]
    transcript_measurements = {}
    exon_measurements = OrderedDict()

    if sample_ids and measurement_type:
        # Get transcript measurements
        query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).filter_by(transcript_id=transcript.id).all()
        for transcript_measurement in query:
            sample = transcript_measurement.sample
            transcript_measurements[sample] = transcript_measurement[measurement_type[0]]

        # Get exon measurements
        query = db.session.query(ExonMeasurement).join(Exon).join(exons_transcripts).filter(exons_transcripts.columns.transcript_id == transcript.id).filter(ExonMeasurement.sample_id.in_(sample_ids)).order_by(Exon.start).options(joinedload(ExonMeasurement.exon, innerjoin=True)).all()
        for exon_measurement in query:
            sample = exon_measurement.sample
            exon = exon_measurement.exon

            # Store exon_measurement per exon and sample
            if exon not in exon_measurements:
                exon_measurements[exon] = {}
            exon_measurements[exon][sample] = exon_measurement[measurement_type[0]]

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

    return render_template('custom_panel_transcript.html', form=custom_panel_form, transcript=transcript, custom_panel=custom_panel, measurement_type=measurement_type, transcript_measurements=transcript_measurements, exon_measurements=exon_measurements)


@app.route('/panel/custom/<int:id>/gene/<string:gene_id>', methods=['GET', 'POST'])
@login_required
def custom_panel_gene(id, gene_id):
    """Custom panel gene page."""
    # TODO: Page layout
    custom_panel = CustomPanel.query.options(joinedload('samples')).get_or_404(id)
    gene = Gene.query.get_or_404(gene_id)

    custom_panel_form = CustomPanelForm()

    sample_ids = [sample.id for sample in custom_panel.samples]
    measurement_type = [custom_panel_form.data['measurement_type'], dict(custom_panel_form.measurement_type.choices).get(custom_panel_form.data['measurement_type'])]
    transcript_measurements = {}

    if sample_ids and measurement_type:
        query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).join(Transcript).filter_by(gene_id=gene_id).options(joinedload('sample')).options(joinedload('transcript')).all()
        for transcript_measurement in query:
            sample = transcript_measurement.sample
            transcript = transcript_measurement.transcript

            if transcript not in transcript_measurements:
                transcript_measurements[transcript] = {}
            transcript_measurements[transcript][sample] = transcript_measurement[measurement_type[0]]

        for transcript in transcript_measurements:
            values = transcript_measurements[transcript].values()
            transcript_measurements[transcript]['min'] = min(values)
            transcript_measurements[transcript]['max'] = max(values)
            transcript_measurements[transcript]['mean'] = float(sum(values)) / len(values)

    return render_template('custom_panel_gene.html', form=custom_panel_form, gene=gene, samples=samples, custom_panel=custom_panel, measurement_type=measurement_type, transcript_measurements=transcript_measurements)
