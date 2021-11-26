"""ExonCov views."""

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
    TranscriptMeasurement, panels_transcripts
)
from .forms import (
    MeasurementTypeForm, CustomPanelForm, CustomPanelNewForm, CustomPanelValidateForm, SampleForm,
    CreatePanelForm, PanelNewVersionForm, PanelEditForm, PanelVersionEditForm, SampleSetPanelGeneForm, SampleGeneForm
)
from .utils import get_summary_stats, get_summary_stats_multi_sample, weighted_average


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/')
@app.route('/sample')
@login_required
def samples():
    """Sample overview page."""
    sample_form = SampleForm(request.args, meta={'csrf': False})
    page = request.args.get('page', default=1, type=int)
    sample = request.args.get('sample')
    sample_type = request.args.get('sample_type')
    project = request.args.get('project')
    run = request.args.get('run')
    samples_per_page = 10

    samples = (
        Sample.query
        .order_by(Sample.import_date.desc())
        .order_by(Sample.name.asc())
        .options(joinedload('sequencing_runs'))
        .options(joinedload('project'))
    )

    if (sample or project or run or sample_type) and sample_form.validate():
        if sample:
            samples = samples.filter(Sample.name.like('%{0}%'.format(sample)))
        if sample_type:
            samples = samples.filter(Sample.type == sample_type)
        if project:
            samples = samples.join(SampleProject).filter(SampleProject.name.like('%{0}%'.format(project)))
        if run:
            samples = samples.join(SequencingRun, Sample.sequencing_runs).filter(or_(SequencingRun.name.like('%{0}%'.format(run)), SequencingRun.platform_unit.like('%{0}%'.format(run))))
        samples = samples.paginate(page=page, per_page=samples_per_page)
    else:
        samples = samples.paginate(page=page, per_page=samples_per_page)

    return render_template('samples.html', form=sample_form, samples=samples)


@app.route('/sample/<int:id>', methods=['GET', 'POST'])
@login_required
def sample(id):
    """Sample page."""

    # Setup gene form and validate
    gene_form = SampleGeneForm()

    if gene_form.validate_on_submit():
        if gene_form.gene_id:
            return redirect(url_for('sample_gene', sample_id=id, gene_id=gene_form.gene_id))

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
        'measurement_percentage30': '>30'
    }
    panels = {}

    for panel, transcript_measurement in query:
        if panel.id not in panels:
            panels[panel.id] = {
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
    return render_template('sample.html', sample=sample, panels=panels, measurement_types=measurement_types, form=gene_form)


@app.route('/sample/<int:id>/inactive_panels')
@login_required
def sample_inactive_panels(id):
    """Sample inactive panels page."""
    sample = Sample.query.options(joinedload('sequencing_runs')).options(joinedload('project')).get_or_404(id)
    measurement_types = {
        'measurement_mean_coverage': 'Mean coverage',
        'measurement_percentage10': '>10',
        'measurement_percentage15': '>15',
        'measurement_percentage30': '>30'
    }
    query = db.session.query(PanelVersion, TranscriptMeasurement).filter_by(active=False).filter_by(validated=True).join(Transcript, PanelVersion.transcripts).join(TranscriptMeasurement).filter_by(sample_id=sample.id).order_by(PanelVersion.panel_name).all()
    panels = {}

    for panel, transcript_measurement in query:
        if panel.id not in panels:
            panels[panel.id] = {
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
    return render_template('sample_inactive_panels.html', sample=sample, panels=panels, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/panel/<int:panel_id>')
@login_required
def sample_panel(sample_id, panel_id):
    """Sample panel page."""
    sample = Sample.query.options(joinedload('sequencing_runs')).options(joinedload('project')).get_or_404(sample_id)
    panel = PanelVersion.query.options(joinedload('core_genes')).get_or_404(panel_id)

    measurement_types = {
        'measurement_mean_coverage': 'Mean coverage',
        'measurement_percentage10': '>10',
        'measurement_percentage15': '>15',
        'measurement_percentage30': '>30'
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
        'core_genes': ', '.join(
            ['{}({}) = {:.2f}%'.format(tm[0].gene, tm[0], tm[1].measurement_percentage15) for tm in transcript_measurements if tm[0].gene in panel.core_genes and tm[1].measurement_percentage15 < 100]
        ),
        'genes_15': ', '.join(
            ['{}({}) = {:.2f}%'.format(tm[0].gene, tm[0], tm[1].measurement_percentage15) for tm in transcript_measurements if tm[0].gene not in panel.core_genes and tm[1].measurement_percentage15 < 95]
        )
    }

    return render_template(
        'sample_panel.html',
        sample=sample,
        panel=panel,
        transcript_measurements=transcript_measurements,
        measurement_types=measurement_types,
        panel_summary=panel_summary
    )


@app.route('/sample/<int:sample_id>/transcript/<string:transcript_name>')
@login_required
def sample_transcript(sample_id, transcript_name):
    """Sample transcript page."""
    sample = Sample.query.options(joinedload('sequencing_runs')).options(joinedload('project')).get_or_404(sample_id)
    transcript = Transcript.query.filter_by(name=transcript_name).options(joinedload('exons')).first()

    exon_measurements = []
    try:
        sample_tabix = pysam.TabixFile(sample.exon_measurement_file)
    except IOError:
        pass
    else:
        with sample_tabix:
            header = sample_tabix.header[0].lstrip('#').split('\t')

            for exon in transcript.exons:
                for row in sample_tabix.fetch(exon.chr, exon.start, exon.end):
                    row = dict(zip(header, row.split('\t')))
                    if int(row['start']) == exon.start and int(row['end']) == exon.end:
                        row['len'] = exon.len
                        exon_measurements.append(row)
                        break

    measurement_types = {
        'measurement_mean_coverage': 'Mean coverage',
        'measurement_percentage10': '>10',
        'measurement_percentage15': '>15',
        'measurement_percentage30': '>30'
    }
    return render_template('sample_transcript.html', sample=sample, transcript=transcript, exon_measurements=exon_measurements, measurement_types=measurement_types)


@app.route('/sample/<int:sample_id>/gene/<string:gene_id>')
@login_required
def sample_gene(sample_id, gene_id):
    """Sample gene page."""
    sample = Sample.query.options(joinedload('sequencing_runs')).options(joinedload('project')).get_or_404(sample_id)
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
    return render_template('panels.html', panels=panels, custom_panels=custom_panels)


@app.route('/panel/<string:name>')
@login_required
def panel(name):
    """Panel page."""
    panel = Panel.query.filter_by(name=name).options(joinedload('versions').joinedload('transcripts')).first_or_404()
    return render_template('panel.html', panel=panel)


@app.route('/panel/<string:name>/new_version', methods=['GET', 'POST'])
@login_required
@roles_required('panel_admin')
def panel_new_version(name):
    """Create new panel version page."""
    panel = Panel.query.filter_by(name=name).options(joinedload('versions').joinedload('transcripts')).first_or_404()
    panel_last_version = panel.last_version

    genes = '\n'.join([transcript.gene_id for transcript in panel_last_version.transcripts])
    core_genes = '\n'.join([gene.id for gene in panel_last_version.core_genes])
    panel_new_version_form = PanelNewVersionForm(
        gene_list=genes,
        core_gene_list=core_genes,
        coverage_requirement_15=panel_last_version.coverage_requirement_15
    )

    if panel_new_version_form.validate_on_submit():
        transcripts = panel_new_version_form.transcripts

        # Check for panel changes
        if sorted(transcripts) == sorted(panel_last_version.transcripts):
            panel_new_version_form.gene_list.errors.append('No changes.')

        else:
            # Create new panel if confirmed or show confirm page.
            # Determine version number
            year = int(time.strftime('%y'))
            if panel_last_version.version_year == year:
                revision = panel_last_version.version_revision + 1
            else:
                revision = 1

            if panel_new_version_form.confirm.data:
                panel_new_version = PanelVersion(
                    panel_name=panel.name,
                    version_year=year,
                    version_revision=revision,
                    transcripts=transcripts,
                    core_genes=panel_new_version_form.core_genes,
                    coverage_requirement_15=panel_new_version_form.coverage_requirement_15.data,
                    comments=panel_new_version_form.data['comments'],
                    user=current_user
                )
                db.session.add(panel_new_version)
                db.session.commit()
                return redirect(url_for('panel', name=panel.name))
            else:
                return render_template(
                    'panel_new_version_confirm.html',
                    form=panel_new_version_form,
                    panel=panel_last_version,
                    year=year,
                    revision=revision
                )

    return render_template('panel_new_version.html', form=panel_new_version_form, panel=panel_last_version)


@app.route('/panel/<string:name>/edit', methods=['GET', 'POST'])
@roles_required('panel_admin')
def panel_edit(name):
    """Set validation status to true."""
    panel = Panel.query.filter_by(name=name).first_or_404()
    panel_edit_form = PanelEditForm(
        comments=panel.comments,
        disease_description_eng=panel.disease_description_eng,
        disease_description_nl=panel.disease_description_nl,
        patientfolder_alissa=panel.patientfolder_alissa,
        clinic_contact=panel.clinic_contact,
        staff_member=panel.staff_member,
    )

    if panel_edit_form.validate_on_submit():
        panel.comments = panel_edit_form.comments.data
        panel.disease_description_eng = panel_edit_form.disease_description_eng.data
        panel.disease_description_nl = panel_edit_form.disease_description_nl.data
        panel.patientfolder_alissa = panel_edit_form.patientfolder_alissa.data
        panel.clinic_contact = panel_edit_form.clinic_contact.data
        panel.staff_member = panel_edit_form.staff_member.data

        db.session.add(panel)
        db.session.commit()
        return redirect(url_for('panel', name=panel.name))

    return render_template('panel_edit.html', form=panel_edit_form, panel=panel)


@app.route('/panel/new', methods=['GET', 'POST'])
@login_required
@roles_required('panel_admin')
def panel_new():
    """Create new panel page."""
    new_panel_form = CreatePanelForm()

    if new_panel_form.validate_on_submit():
        panel_name = new_panel_form.data['name']
        transcripts = new_panel_form.transcripts
        core_genes = new_panel_form.core_genes

        new_panel = Panel(
            name=panel_name,
            comments=new_panel_form.comments.data,
            disease_description_eng=new_panel_form.disease_description_eng.data,
            disease_description_nl=new_panel_form.disease_description_nl.data,
            patientfolder_alissa=new_panel_form.patientfolder_alissa.data,
            clinic_contact=new_panel_form.clinic_contact.data,
            staff_member=new_panel_form.staff_member.data
        )

        new_panel_version = PanelVersion(
            panel_name=panel_name,
            version_year=time.strftime('%y'),
            version_revision=1,
            transcripts=transcripts,
            core_genes=core_genes,
            coverage_requirement_15=new_panel_form.coverage_requirement_15.data,
            comments=new_panel_form.comments.data,
            user=current_user
            )

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


@app.route('/panel_version/<int:id>/edit', methods=['GET', 'POST'])
@roles_required('panel_admin')
def panel_version_edit(id):
    """Set validation status to true."""
    panel = PanelVersion.query.get_or_404(id)
    core_genes = '\n'.join([gene.id for gene in panel.core_genes])

    form = PanelVersionEditForm(
        active=panel.active,
        validated=panel.validated,
        comments=panel.comments,
        coverage_requirement_15=panel.coverage_requirement_15,
        core_gene_list=core_genes
    )

    if form.validate_on_submit():
        panel.active = form.active.data
        if not panel.validated:  # only update if panel not yet validated.
            panel.validated = form.validated.data
        panel.comments = form.comments.data
        panel.coverage_requirement_15 = form.coverage_requirement_15.data
        panel.core_genes = form.core_genes
        db.session.add(panel)
        db.session.commit()
        return redirect(url_for('panel_version', id=panel.id))

    return render_template('panel_version_edit.html', form=form, panel=panel)


@app.route('/panel/custom')
@login_required
def custom_panels():
    """Custom panel overview page."""
    custom_panel_form = CustomPanelForm(request.args, meta={'csrf': False})
    page = request.args.get('page', default=1, type=int)
    search = request.args.get('search')

    custom_panels = CustomPanel.query.order_by(CustomPanel.id.desc())

    if search and custom_panel_form.validate():
        custom_panels = custom_panels.filter(or_(
            CustomPanel.id.like('%{0}%'.format(search)),
            CustomPanel.research_number.like('%{0}%'.format(search)),
            CustomPanel.comments.like('%{0}%'.format(search)),
        ))

    custom_panels = custom_panels.paginate(page=page, per_page=15)

    return render_template('custom_panels.html', form=custom_panel_form, custom_panels=custom_panels)


@app.route('/panel/custom/new', methods=['GET', 'POST'])
@login_required
def custom_panel_new():
    """New custom panel page."""
    custom_panel_form = CustomPanelNewForm()

    if custom_panel_form.validate_on_submit():
        samples = []
        if custom_panel_form.data['samples']:
            samples += custom_panel_form.data['samples']
        if custom_panel_form.data['sample_set']:
            samples += custom_panel_form.data['sample_set'].samples

        custom_panel = CustomPanel(
            created_by=current_user,
            transcripts=custom_panel_form.transcripts,
            samples=samples,
            research_number=custom_panel_form.data['research_number'],
            comments=custom_panel_form.data['comments']
        )
        db.session.add(custom_panel)
        db.session.commit()
        return redirect(url_for('custom_panel', id=custom_panel.id))

    return render_template('custom_panel_new.html', form=custom_panel_form)


@app.route('/panel/custom/<int:id>', methods=['GET', 'POST'])
@login_required
def custom_panel(id):
    """Custom panel page."""
    custom_panel = CustomPanel.query.options(joinedload('transcripts')).options(joinedload('samples')).get_or_404(id)
    measurement_type_form = MeasurementTypeForm()

    sample_ids = [sample.id for sample in custom_panel.samples]
    transcript_ids = [transcript.id for transcript in custom_panel.transcripts]
    measurement_type = [measurement_type_form.data['measurement_type'], dict(measurement_type_form.measurement_type.choices).get(measurement_type_form.data['measurement_type'])]
    transcript_measurements = {}
    panel_measurements = {}
    sample_stats = {sample: [[], {}] for sample in custom_panel.samples}

    query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).filter(TranscriptMeasurement.transcript_id.in_(transcript_ids)).options(joinedload('transcript').joinedload('gene')).all()

    for transcript_measurement in query:
        sample = transcript_measurement.sample
        transcript = transcript_measurement.transcript

        # Store transcript_measurements per transcript and sample
        if transcript not in transcript_measurements:
            transcript_measurements[transcript] = {}
        transcript_measurements[transcript][sample] = transcript_measurement[measurement_type[0]]

        if transcript_measurement[measurement_type[0]] == 100:
            sample_stats[sample][0].append('{0}({1})'.format(transcript.gene.id, transcript.name))
        else:
            sample_stats[sample][1]['{0}({1})'.format(transcript.gene.id, transcript.name)] = transcript_measurement[measurement_type[0]]

        # Calculate weighted average per sample for entire panel
        if sample not in panel_measurements:
            panel_measurements[sample] = {
                'len': transcript_measurement.len,
                'measurement': transcript_measurement[measurement_type[0]]
            }
        else:
            panel_measurements[sample]['measurement'] = weighted_average(
                values=[panel_measurements[sample]['measurement'], transcript_measurement[measurement_type[0]]],
                weights=[panel_measurements[sample]['len'], transcript_measurement.len]
            )
            panel_measurements[sample]['len'] += transcript_measurement.len

    # Calculate min, mean, max
    transcript_measurements = get_summary_stats_multi_sample(measurements=transcript_measurements)

    values = [panel_measurements[sample]['measurement'] for sample in panel_measurements]
    panel_measurements['min'], panel_measurements['max'], panel_measurements['mean'] = get_summary_stats(values)
    return render_template('custom_panel.html', form=measurement_type_form, custom_panel=custom_panel, measurement_type=measurement_type, transcript_measurements=transcript_measurements, panel_measurements=panel_measurements, sample_stats=sample_stats)


@app.route('/panel/custom/<int:id>/transcript/<string:transcript_name>', methods=['GET', 'POST'])
@login_required
def custom_panel_transcript(id, transcript_name):
    """Custom panel transcript page."""
    custom_panel = CustomPanel.query.options(joinedload('samples')).get_or_404(id)
    measurement_type_form = MeasurementTypeForm()

    sample_ids = [sample.id for sample in custom_panel.samples]
    transcript = Transcript.query.filter_by(name=transcript_name).options(joinedload('gene')).options(joinedload('exons')).first()
    measurement_type = [measurement_type_form.data['measurement_type'], dict(measurement_type_form.measurement_type.choices).get(measurement_type_form.data['measurement_type'])]
    transcript_measurements = {}
    exon_measurements = {}

    if sample_ids and measurement_type:
        # Get transcript measurements
        query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).filter_by(transcript_id=transcript.id).all()
        for transcript_measurement in query:
            sample = transcript_measurement.sample
            transcript_measurements[sample] = transcript_measurement[measurement_type[0]]

        # Get exon measurements
        for sample in custom_panel.samples:
            try:
                sample_tabix = pysam.TabixFile(sample.exon_measurement_file)
            except IOError:
                exon_measurements = {}
                break
            else:
                with sample_tabix:
                    header = sample_tabix.header[0].lstrip('#').split('\t')

                    for exon in transcript.exons:
                        if exon not in exon_measurements:
                            exon_measurements[exon] = {}

                        for row in sample_tabix.fetch(exon.chr, exon.start, exon.end):
                            row = dict(zip(header, row.split('\t')))
                            if int(row['start']) == exon.start and int(row['end']) == exon.end:
                                exon_measurements[exon][sample] = float(row[measurement_type[0]])
                                break

        # Calculate min, mean, max
        transcript_measurements['min'], transcript_measurements['max'], transcript_measurements['mean'] = get_summary_stats(
            transcript_measurements.values()
        )

        exon_measurements = get_summary_stats_multi_sample(measurements=exon_measurements)

    return render_template('custom_panel_transcript.html', form=measurement_type_form, transcript=transcript, custom_panel=custom_panel, measurement_type=measurement_type, transcript_measurements=transcript_measurements, exon_measurements=exon_measurements)


@app.route('/panel/custom/<int:id>/gene/<string:gene_id>', methods=['GET', 'POST'])
@login_required
def custom_panel_gene(id, gene_id):
    """Custom panel gene page."""
    custom_panel = CustomPanel.query.get_or_404(id)
    gene = Gene.query.get_or_404(gene_id)

    measurement_type_form = MeasurementTypeForm()

    sample_ids = [sample.id for sample in custom_panel.samples]
    measurement_type = [measurement_type_form.data['measurement_type'], dict(measurement_type_form.measurement_type.choices).get(measurement_type_form.data['measurement_type'])]
    transcript_measurements = {}

    if sample_ids and measurement_type:
        query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).join(Transcript).filter_by(gene_id=gene_id).options(joinedload('sample')).options(joinedload('transcript')).all()
        for transcript_measurement in query:
            sample = transcript_measurement.sample
            transcript = transcript_measurement.transcript

            if transcript not in transcript_measurements:
                transcript_measurements[transcript] = {}
            transcript_measurements[transcript][sample] = transcript_measurement[measurement_type[0]]

        transcript_measurements = get_summary_stats_multi_sample(measurements=transcript_measurements)

    return render_template('custom_panel_gene.html', form=measurement_type_form, gene=gene, custom_panel=custom_panel, measurement_type=measurement_type, transcript_measurements=transcript_measurements)


@app.route('/panel/custom/<int:id>/set_validated', methods=['GET', 'POST'])
@login_required
def custom_panel_validated(id):
    """Set validation status to true."""
    custom_panel = CustomPanel.query.get_or_404(id)

    custom_panel_validate_form = CustomPanelValidateForm()

    if custom_panel_validate_form.validate_on_submit():

        custom_panel.validated = True
        custom_panel.validated_by = current_user
        custom_panel.validated_date = datetime.date.today()
        db.session.add(custom_panel)
        db.session.commit()

        return redirect(url_for('custom_panel', id=custom_panel.id))
    else:
        return render_template('custom_panel_validate_confirm.html', form=custom_panel_validate_form, custom_panel=custom_panel)


@app.route('/sample_set', methods=['GET', 'POST'])
@login_required
def sample_sets():
    """Sample sets page."""
    sample_sets = SampleSet.query.options(joinedload('samples')).filter_by(active=True).all()

    panel_gene_form = SampleSetPanelGeneForm()

    if panel_gene_form.validate_on_submit():
        if panel_gene_form.panel.data:
            return redirect(url_for('sample_set_panel', sample_set_id=panel_gene_form.sample_set.data.id, panel_id=panel_gene_form.panel.data.id))
        elif panel_gene_form.gene_id:
            return redirect(url_for('sample_set_gene', sample_set_id=panel_gene_form.sample_set.data.id, gene_id=panel_gene_form.gene_id))

    return render_template('sample_sets.html', sample_sets=sample_sets, form=panel_gene_form)


@app.route('/sample_set/<int:id>', methods=['GET', 'POST'])
@login_required
def sample_set(id):
    """Sample set page."""
    sample_set = SampleSet.query.options(joinedload('samples')).get_or_404(id)
    measurement_type_form = MeasurementTypeForm()

    sample_ids = [sample.id for sample in sample_set.samples]
    measurement_type = [
        measurement_type_form.data['measurement_type'], 
        dict(measurement_type_form.measurement_type.choices).get(measurement_type_form.data['measurement_type'])
    ]
    panels_measurements = {}

    query = (
        db.session.query(PanelVersion, TranscriptMeasurement)
        .filter_by(active=True)
        .filter_by(validated=True)
        .join(Transcript, PanelVersion.transcripts)
        .join(TranscriptMeasurement)
        .filter(TranscriptMeasurement.sample_id.in_(sample_ids))
        .order_by(PanelVersion.panel_name)
        .all()
    )

    for panel, transcript_measurement in query:
        sample = transcript_measurement.sample
        if panel not in panels_measurements:
            panels_measurements[panel] = {
                'panel': panel,
                'samples': {},
            }

        if sample not in panels_measurements[panel]['samples']:
            panels_measurements[panel]['samples'][sample] = {
                'len': transcript_measurement.len,
                'measurement': transcript_measurement[measurement_type[0]]
            }
        else:
            panels_measurements[panel]['samples'][sample]['measurement'] = weighted_average(
                values=[panels_measurements[panel]['samples'][sample]['measurement'], transcript_measurement[measurement_type[0]]],
                weights=[panels_measurements[panel]['samples'][sample]['len'], transcript_measurement.len]
            )
            panels_measurements[panel]['samples'][sample]['len'] += transcript_measurement.len

    panels_measurements = get_summary_stats_multi_sample(measurements=panels_measurements, samples=sample_set.samples)

    return render_template('sample_set.html', sample_set=sample_set, form=measurement_type_form, measurement_type=measurement_type, panels_measurements=panels_measurements)


@app.route('/sample_set/<int:sample_set_id>/panel/<int:panel_id>', methods=['GET', 'POST'])
@login_required
def sample_set_panel(sample_set_id, panel_id):
    """Sample set panel page."""
    sample_set = SampleSet.query.options(joinedload('samples')).get_or_404(sample_set_id)
    panel = PanelVersion.query.options(joinedload('transcripts')).get_or_404(panel_id)
    measurement_type_form = MeasurementTypeForm()

    sample_ids = [sample.id for sample in sample_set.samples]
    transcript_ids = [transcript.id for transcript in panel.transcripts]
    measurement_type = [measurement_type_form.data['measurement_type'], dict(measurement_type_form.measurement_type.choices).get(measurement_type_form.data['measurement_type'])]
    transcript_measurements = {}

    query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).filter(TranscriptMeasurement.transcript_id.in_(transcript_ids)).options(joinedload('transcript').joinedload('gene')).all()

    for transcript_measurement in query:
        sample = transcript_measurement.sample
        transcript = transcript_measurement.transcript

        # Store transcript_measurements per transcript and sample
        if transcript not in transcript_measurements:
            transcript_measurements[transcript] = {}
        transcript_measurements[transcript][sample] = transcript_measurement[measurement_type[0]]

    # Calculate min, mean, max
    transcript_measurements = get_summary_stats_multi_sample(measurements=transcript_measurements)

    return render_template('sample_set_panel.html', sample_set=sample_set, form=measurement_type_form, measurement_type=measurement_type, panel=panel, transcript_measurements=transcript_measurements)


@app.route('/sample_set/<int:sample_set_id>/transcript/<string:transcript_name>', methods=['GET', 'POST'])
@login_required
def sample_set_transcript(sample_set_id, transcript_name):
    """Sample set transcript page."""
    sample_set = SampleSet.query.options(joinedload('samples')).get_or_404(sample_set_id)
    transcript = Transcript.query.filter_by(name=transcript_name).options(joinedload('gene')).options(joinedload('exons')).first()
    measurement_type_form = MeasurementTypeForm()

    measurement_type = [measurement_type_form.data['measurement_type'], dict(measurement_type_form.measurement_type.choices).get(measurement_type_form.data['measurement_type'])]
    exon_measurements = {}

    # Get exon measurements
    for sample in sample_set.samples:
        try:
            sample_tabix = pysam.TabixFile(sample.exon_measurement_file)
        except IOError:
            exon_measurements = {}
            break
        else:
            with sample_tabix:
                header = sample_tabix.header[0].lstrip('#').split('\t')

                for exon in transcript.exons:
                    if exon not in exon_measurements:
                        exon_measurements[exon] = {}

                    for row in sample_tabix.fetch(exon.chr, exon.start, exon.end):
                        row = dict(zip(header, row.split('\t')))
                        if int(row['start']) == exon.start and int(row['end']) == exon.end:
                            exon_measurements[exon][sample] = float(row[measurement_type[0]])
                            break

        exon_measurements = get_summary_stats_multi_sample(measurements=exon_measurements)

    return render_template('sample_set_transcript.html', form=measurement_type_form, transcript=transcript, sample_set=sample_set, measurement_type=measurement_type, exon_measurements=exon_measurements)


@app.route('/sample_set/<int:sample_set_id>/gene/<string:gene_id>', methods=['GET', 'POST'])
@login_required
def sample_set_gene(sample_set_id, gene_id):
    """Sample set gene page."""
    sample_set = SampleSet.query.options(joinedload('samples')).get_or_404(sample_set_id)
    gene = Gene.query.get_or_404(gene_id)
    measurement_type_form = MeasurementTypeForm()

    sample_ids = [sample.id for sample in sample_set.samples]
    measurement_type = [measurement_type_form.data['measurement_type'], dict(measurement_type_form.measurement_type.choices).get(measurement_type_form.data['measurement_type'])]
    transcript_measurements = {}

    if sample_ids and measurement_type:
        query = TranscriptMeasurement.query.filter(TranscriptMeasurement.sample_id.in_(sample_ids)).join(Transcript).filter_by(gene_id=gene_id).options(joinedload('sample')).options(joinedload('transcript')).all()
        for transcript_measurement in query:
            sample = transcript_measurement.sample
            transcript = transcript_measurement.transcript

            if transcript not in transcript_measurements:
                transcript_measurements[transcript] = {}
            transcript_measurements[transcript][sample] = transcript_measurement[measurement_type[0]]

        transcript_measurements = get_summary_stats_multi_sample(measurements=transcript_measurements)

    return render_template('sample_set_gene.html', form=measurement_type_form, gene=gene, sample_set=sample_set, measurement_type=measurement_type, transcript_measurements=transcript_measurements)
