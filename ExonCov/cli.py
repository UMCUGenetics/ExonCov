"""CLI functions."""

import sys
import re
import time
import subprocess
import os
import shlex
import urllib

from flask_script import Command, Option
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
import tempfile
import shutil
import pysam

from . import app, db, utils
from .models import Gene, GeneAlias, Transcript, Exon, SequencingRun, Sample, SampleProject, TranscriptMeasurement, Panel, PanelVersion, CustomPanel
from .utils import weighted_average


class PrintStats(Command):
    """Print database stats."""

    def run(self):
        print("Number of genes: {0}".format(Gene.query.count()))
        print("Number of transcripts: {0}".format(Transcript.query.count()))
        print("Number of exons: {0}".format(Exon.query.count()))
        print("Number of panels: {0}".format(Panel.query.count()))
        print("Number of custom panels: {0}".format(CustomPanel.query.count()))
        print("Number of samples: {0}".format(Sample.query.count()))
        print("Number of sequencing runs: {0}".format(SequencingRun.query.count()))
        print("Number of sequencing projects: {0}".format(SampleProject.query.count()))

        print("Number of projects and samples per year:")
        projects_year = {}
        for project in SampleProject.query.options(joinedload('samples')):
            if project.name[0:6].isdigit() and project.samples:
                project_year = project.name[0:2]
                if project_year not in projects_year:
                    projects_year[project_year] = [0, 0]
                projects_year[project_year][0] += 1
                projects_year[project_year][1] += len(project.samples)

        print("Year\tProjects\tSamples")
        for year, count in sorted(projects_year.items()):
            print("{year}\t{project_count}\t{sample_count}".format(year=year, project_count=count[0], sample_count=count[1]))


class PrintPanelGenesTable(Command):
    """Print tab delimited panel / genes table."""

    def run(self):
        print('{panel}\t{genes}'.format(panel='panel_version', genes='genes'))

        panel_versions = PanelVersion.query.filter_by(active=True).options(joinedload('transcripts'))

        for panel in panel_versions:
            print('{panel}\t{genes}'.format(
                panel=panel.name_version,
                genes='\t'.join([transcript.gene_id for transcript in panel.transcripts])
            ))


class PrintTranscripts(Command):
    """Print tab delimited gene / transcript table"""

    option_list = (
        Option('-p', '--preferred_transcripts', dest='preferred_transcripts', default=False, action='store_true', help="Print preferred transcripts only"),
    )

    def run(self, preferred_transcripts):
        print('{gene}\t{transcript}'.format( gene='Gene', transcript='Transcript'))

        genes = Gene.query.options(joinedload('transcripts'))

        for gene in genes:
            if preferred_transcripts:
                print('{gene}\t{transcript}'.format(gene=gene.id, transcript=gene.default_transcript.name))
            else:
                for transcript in gene.transcripts:
                    print('{gene}\t{transcript}'.format(gene=gene.id,transcript=transcript.name))


class ImportBam(Command):
    """Import sample from bam file."""

    option_list = (
        Option('project_name'),
        Option('bam'),
        Option('-b', '--exon_bed', dest='exon_bed_file', default=app.config['EXON_BED_FILE']),
        Option('-t', '--threads', dest='threads', default=1),
        Option('-f', '--overwrite', dest='overwrite', default=False, action='store_true'),
        Option('-o', '--print_output', dest='print_output', default=False, action='store_true'),
        Option('--temp', dest='temp_path', default=None),
    )

    def run(self, bam, project_name, exon_bed_file, threads, overwrite, print_output, temp_path):
        try:
            bam_file = pysam.AlignmentFile(bam, "rb")
        except IOError as e:
            sys.exit(e)

        sample_name = None
        sequencing_runs = {}
        sequencing_run_ids = []
        exon_measurements = {}

        # Parse read groups and setup sequencing run(s)
        for read_group in bam_file.header['RG']:
            if not sample_name:
                sample_name = read_group['SM']
            elif sample_name != read_group['SM']:
                sys.exit("ERROR: Exoncov does not support bam files containing multiple samples.")

            if read_group['PU'] not in sequencing_runs:
                sequencing_run, sequencing_run_exists = utils.get_one_or_create(
                    db.session,
                    SequencingRun,
                    platform_unit=read_group['PU']
                )  # returns object and exists bool
                sequencing_runs[read_group['PU']] = sequencing_run
                sequencing_run_ids.append(sequencing_run.id)

        if not sequencing_runs:
            sys.exit("ERROR: Sample can not be linked to a sequencing run, please make sure that read groups contain PU values.")

        bam_file.close()

        # Setup sample project
        sample_project, sample_project_exists = utils.get_one_or_create(
            db.session,
            SampleProject,
            name=project_name
        )  # returns object and exists bool

        # Look for sample in database
        sample = Sample.query.filter_by(name=sample_name).filter_by(project_id=sample_project.id).first()
        if sample and overwrite:
            db.session.delete(sample)
            db.session.commit()
        elif sample and not overwrite:
            sys.exit("ERROR: Sample and project combination already exists.\t{0}".format(sample))

        # Create sambamba command
        sambamba_command = "{sambamba} depth region {bam_file} --nthreads {threads} --filter '{filter}' --regions {bed_file} {settings}".format(
            sambamba=app.config['SAMBAMBA'],
            bam_file=bam,
            threads=threads,
            filter=app.config['SAMBAMBA_FILTER'],
            bed_file=exon_bed_file,
            settings='--fix-mate-overlaps --min-base-quality 10 --cov-threshold 10 --cov-threshold 15 --cov-threshold 20 --cov-threshold 30 --cov-threshold 50 --cov-threshold 100',
        )

        # Create sample
        sample = Sample(
            name=sample_name,
            project=sample_project,
            file_name=bam,
            import_command=sambamba_command,
            sequencing_runs=sequencing_runs.values(),
            exon_measurement_file='{0}_{1}'.format(sample_project.name, sample_name)
            )
        db.session.add(sample)
        db.session.commit()

        # Add sample id to exon measurement file
        sample.exon_measurement_file = '{0}_{1}.txt'.format(sample.id, sample.exon_measurement_file)
        db.session.add(sample)
        db.session.commit()

        # Create temp_dir
        if not temp_path:
            temp_dir = tempfile.mkdtemp()
        else:  # assume path exist and user is responsible for this directory
            temp_dir = temp_path

        # Run sambamba
        p = subprocess.Popen(shlex.split(sambamba_command), stdout=subprocess.PIPE)
        exon_measurement_file_path = '{0}/{1}'.format(temp_dir, sample.exon_measurement_file)
        with open(exon_measurement_file_path, "w") as exon_measurement_file:
            for line in p.stdout:
                if print_output:
                    print(line)

                # Header
                if line.startswith('#'):
                    header = line.rstrip().split('\t')
                    measurement_mean_coverage_index = header.index('meanCoverage')
                    measurement_percentage10_index = header.index('percentage10')
                    measurement_percentage15_index = header.index('percentage15')
                    measurement_percentage20_index = header.index('percentage20')
                    measurement_percentage30_index = header.index('percentage30')
                    measurement_percentage50_index = header.index('percentage50')
                    measurement_percentage100_index = header.index('percentage100')
                    exon_measurement_file.write(
                        '#{chr}\t{start}\t{end}\t{cov}\t{perc_10}\t{perc_15}\t{perc_20}\t{perc_30}\t{perc_50}\t{perc_100}\n'.format(
                            chr='chr',
                            start='start',
                            end='end',
                            cov='measurement_mean_coverage',
                            perc_10='measurement_percentage10',
                            perc_15='measurement_percentage15',
                            perc_20='measurement_percentage20',
                            perc_30='measurement_percentage30',
                            perc_50='measurement_percentage50',
                            perc_100='measurement_percentage100',
                        )
                    )

                # Measurement
                else:
                    data = line.rstrip().split('\t')
                    chr, start, end = data[:3]
                    exon_id = '{0}_{1}_{2}'.format(chr, start, end)
                    measurement_mean_coverage = float(data[measurement_mean_coverage_index])
                    measurement_percentage10 = float(data[measurement_percentage10_index])
                    measurement_percentage15 = float(data[measurement_percentage15_index])
                    measurement_percentage20 = float(data[measurement_percentage20_index])
                    measurement_percentage30 = float(data[measurement_percentage30_index])
                    measurement_percentage50 = float(data[measurement_percentage50_index])
                    measurement_percentage100 = float(data[measurement_percentage100_index])
                    exon_measurement_file.write(
                        '{chr}\t{start}\t{end}\t{cov}\t{perc_10}\t{perc_15}\t{perc_20}\t{perc_30}\t{perc_50}\t{perc_100}\n'.format(
                            chr=chr,
                            start=start,
                            end=end,
                            cov=measurement_mean_coverage,
                            perc_10=measurement_percentage10,
                            perc_15=measurement_percentage15,
                            perc_20=measurement_percentage20,
                            perc_30=measurement_percentage30,
                            perc_50=measurement_percentage50,
                            perc_100=measurement_percentage100,
                        )
                    )

                    exon_measurements[exon_id] = {
                        'sample_id': sample.id,
                        'exon_id': exon_id,
                        'measurement_mean_coverage': measurement_mean_coverage,
                        'measurement_percentage10': measurement_percentage10,
                        'measurement_percentage15': measurement_percentage15,
                        'measurement_percentage20': measurement_percentage20,
                        'measurement_percentage30': measurement_percentage30,
                        'measurement_percentage50': measurement_percentage50,
                        'measurement_percentage100': measurement_percentage100,
                    }

        # Compress, index and rsync
        exon_measurement_file_path_gz = '{0}.gz'.format(exon_measurement_file_path)
        pysam.tabix_compress(exon_measurement_file_path, exon_measurement_file_path_gz)
        pysam.tabix_index(exon_measurement_file_path_gz, seq_col=0, start_col=1, end_col=2)
        os.system('rsync {0}* {1}'.format(exon_measurement_file_path_gz, app.config['EXON_MEASUREMENTS_RSYNC_PATH']))

        # Change exon_measurement_file to path on server.
        sample.exon_measurement_file = '{0}/{1}.gz'.format(
            app.config['EXON_MEASUREMENTS_RSYNC_PATH'].split(':')[-1],
            sample.exon_measurement_file
        )
        db.session.add(sample)
        db.session.commit()

        # Set transcript measurements
        transcripts = Transcript.query.options(joinedload('exons')).all()
        transcripts_measurements = {}

        for transcript in transcripts:
            for exon in transcript.exons:
                exon_measurement = exon_measurements[exon.id]
                if transcript.id not in transcripts_measurements:
                    transcripts_measurements[transcript.id] = {
                        'len': exon.len,
                        'transcript_id': transcript.id,
                        'sample_id': sample.id,
                        'measurement_mean_coverage': exon_measurement['measurement_mean_coverage'],
                        'measurement_percentage10': exon_measurement['measurement_percentage10'],
                        'measurement_percentage15': exon_measurement['measurement_percentage15'],
                        'measurement_percentage20': exon_measurement['measurement_percentage20'],
                        'measurement_percentage30': exon_measurement['measurement_percentage30'],
                        'measurement_percentage50': exon_measurement['measurement_percentage50'],
                        'measurement_percentage100': exon_measurement['measurement_percentage100'],
                    }
                else:
                    measurement_types = ['measurement_mean_coverage', 'measurement_percentage10', 'measurement_percentage15', 'measurement_percentage20', 'measurement_percentage30', 'measurement_percentage50', 'measurement_percentage100']
                    for measurement_type in measurement_types:
                        transcripts_measurements[transcript.id][measurement_type] = weighted_average(
                            [transcripts_measurements[transcript.id][measurement_type], exon_measurement[measurement_type]],
                            [transcripts_measurements[transcript.id]['len'], exon.len]
                        )
                    transcripts_measurements[transcript.id]['len'] += exon.len

        # Bulk insert transcript measurements
        bulk_insert_n = 1000
        transcript_values = transcripts_measurements.values()
        for i in range(0, len(transcript_values), bulk_insert_n):
            db.session.bulk_insert_mappings(TranscriptMeasurement, transcript_values[i:i+bulk_insert_n])
            db.session.commit()

        # Remove temp_dir
        if not temp_path:
            shutil.rmtree(temp_dir)


class SearchSample(Command):
    """Search sample in database."""

    option_list = (
        Option('sample_name'),
    )

    def run(self, sample_name):
        samples = Sample.query.filter_by(name=sample_name).all()

        print("Sample ID\tSample Name\tProject\tSequencing Runs\tCustom Panels")
        for sample in samples:
            print("{id}\t{name}\t{project}\t{runs}\t{custom_panels}".format(
                id=sample.id,
                name=sample.name,
                project=sample.project,
                runs=sample.sequencing_runs,
                custom_panels=sample.custom_panels,
            ))


class RemoveSample(Command):
    """Remove sample from database."""

    option_list = (
        Option('sample_id'),
    )

    def run(self, sample_id):
        sample = Sample.query.get(sample_id)
        if not sample:
            sys.exit("ERROR: Sample not found in the database.")

        elif sample.custom_panels:
            sys.exit("ERROR: Sample is used in custom panels.")

        else:
            db.session.delete(sample)
            db.session.commit()


class CheckSamples(Command):
    """Check transcripts_measurements for all samples."""

    def run(self):
        error = False

        transcript_count = Transcript.query.count()
        sample_transcript_count = db.session.query(Sample.name, func.count(TranscriptMeasurement.id)).outerjoin(TranscriptMeasurement).group_by(Sample.id).all()
        for sample_count in sample_transcript_count:
            if sample_count[1] != transcript_count:
                print("ERROR: Sample:{0} TranscriptMeasurement:{1} Exons:{2}".format(sample_count[0], sample_count[1], transcript_count))
                error = True

        if not error:
            print("No errors found.")


class ImportAliasTable(Command):
    """Import gene aliases from HGNC (ftp://ftp.ebi.ac.uk/pub/databases/genenames/new/tsv/hgnc_complete_set.txt)"""

    def run(self):
        hgnc_file = urllib.urlopen('ftp://ftp.ebi.ac.uk/pub/databases/genenames/new/tsv/hgnc_complete_set.txt')
        header = hgnc_file.readline().strip().split('\t')
        for line in hgnc_file:
            data = line.strip().split('\t')

            # skip lines without locus_group, refseq_accession, gene symbol or alias symbol
            try:
                locus_group = data[header.index('locus_group')]
                refseq_accession = data[header.index('refseq_accession')]
                hgnc_gene_symbol = data[header.index('symbol')]  # Current hgnc gene symbol
                hgnc_prev_symbols = data[header.index('prev_symbol')].strip('"')   # Use only previous gene symbols as aliases
            except IndexError:
                continue

            # Only process protein-coding gene or non-coding RNA with 'NM' refseq_accession
            if (locus_group == 'protein-coding gene' or locus_group == 'non-coding RNA') and 'NM' in refseq_accession and hgnc_prev_symbols:
                # Possible gene id's
                hgnc_gene_ids = [hgnc_gene_symbol]
                hgnc_gene_ids.extend(hgnc_prev_symbols.split('|'))

                # Find gene in database
                db_genes_ids = []
                for hgnc_gene_id in hgnc_gene_ids:
                    db_gene = Gene.query.get(hgnc_gene_id)
                    if db_gene:
                        db_genes_ids.append(db_gene.id)

                # Check db genes
                if not db_genes_ids:
                    print("ERROR: No gene in database found for: {0}".format(','.join(hgnc_gene_ids)))

                # Create aliases
                else:
                    for db_gene_id in db_genes_ids:
                        for hgnc_gene_id in hgnc_gene_ids:
                            if hgnc_gene_id not in db_genes_ids:
                                try:
                                    gene_alias = GeneAlias(id=hgnc_gene_id, gene_id=db_gene_id)
                                    db.session.add(gene_alias)
                                    db.session.commit()
                                except IntegrityError:
                                    db.session.rollback()
                                    continue
                            elif hgnc_gene_id != db_gene_id:  # but does exist as gene in database
                                print("ERROR: Can not import alias: {0} for gene: {1}".format(hgnc_gene_id, db_gene_id))


class PrintPanelBed(Command):
    """Print bed file containing regions in active and validated panels. FULL_autosomal and FULL_TARGET are filtered from the list."""

    option_list = (
        Option('-f', '--remove_flank', dest='remove_flank', default=False, action='store_true', help="Remove 20bp flank from exon coordinates."),
        Option('-p', '--panel', dest='panel', help="Filter on panel name (including version, for example AMY01v19.1).")
    )

    def run(self, remove_flank, panel):
        exons = []

        if panel:
            panel_name, version = panel.split('v')
            version_year, version_revision = version.split('.')
            panel_versions = PanelVersion.query.filter_by(panel_name=panel_name).filter_by(version_year=version_year).filter_by(version_revision=version_revision).options(joinedload('transcripts'))
        else:
            panel_versions = PanelVersion.query.filter_by(active=True).filter_by(validated=True).options(joinedload('transcripts'))

        for panel in panel_versions:
            if 'FULL' not in panel.panel_name:  # skip FULL_autosomal and FULL_TARGET
                for transcript in panel.transcripts:
                    for exon in transcript.exons:
                        if exon.id not in exons:
                            exons.append(exon.id)
                            if remove_flank:
                                print("{chr}\t{start}\t{end}\t{gene}".format(
                                    chr=exon.chr,
                                    start=exon.start + 20,  # Add 20bp to remove flank
                                    end=exon.end - 20,  # Substract 20bp to remove flank
                                    gene=transcript.gene.id
                                ))
                            else:
                                print("{chr}\t{start}\t{end}\t{gene}".format(
                                    chr=exon.chr,
                                    start=exon.start,
                                    end=exon.end,
                                    gene=transcript.gene.id
                                ))


class LoadDesign(Command):
    """Load design files to database."""

    def run(self):
        # files
        exon_file = app.config['EXON_BED_FILE']
        gene_transcript_file = app.config['GENE_TRANSCRIPT_FILE']
        preferred_transcripts_file = app.config['PREFERRED_TRANSCRIPTS_FILE']
        gene_panel_file = app.config['GENE_PANEL_FILE']

        # Filled during parsing.
        transcripts = {}
        exons = []

        # Parse Exon file
        with open(exon_file, 'r') as f:
            print("Loading exon file: {0}".format(exon_file))
            for line in f:
                data = line.rstrip().split('\t')
                chr, start, end = data[:3]
                # Create exon
                exon = Exon(
                    id='{0}_{1}_{2}'.format(chr, start, end),
                    chr=chr,
                    start=int(start),
                    end=int(end)
                )

                try:
                    transcript_data = set(data[6].split(':'))
                except IndexError:
                    print("Warning: No transcripts for exon: {0}.".format(exon))
                    transcript_data = []

                # Create transcripts
                for transcript_name in transcript_data:
                    if transcript_name != 'NA':
                        if transcript_name in transcripts:
                            transcript = transcripts[transcript_name]

                            # Set start / end positions
                            if transcript.start > exon.start:
                                transcript.start = exon.start
                            if transcript.end < exon.end:
                                transcript.end = exon.end

                            # Sanity check chromosome
                            if transcript.chr != exon.chr:
                                print("Warning: Different chromosomes for {0} and {1}".format(transcript, exon))

                        else:
                            transcript = Transcript(
                                name=transcript_name,
                                chr=exon.chr,
                                start=exon.start,
                                end=exon.end
                            )
                            transcripts[transcript_name] = transcript
                        exon.transcripts.append(transcript)
                exons.append(exon)

        # Bulk insert exons and transcript
        bulk_insert_n = 5000
        for i in range(0, len(exons), bulk_insert_n):
            db.session.add_all(exons[i:i+bulk_insert_n])
            db.session.commit()

        db.session.add_all(transcripts.values())
        db.session.commit()

        # Load gene and transcript file
        genes = {}
        with open(gene_transcript_file, 'r') as f:
            print("Loading gene transcript file: {0}".format(gene_transcript_file))
            for line in f:
                if not line.startswith('#'):
                    data = line.rstrip().split('\t')
                    gene_id = data[0].rstrip()
                    transcript_name = data[1].rstrip()

                    if transcript_name in transcripts:
                        if gene_id in genes:
                            gene = genes[gene_id]
                        else:
                            gene = Gene(id=gene_id)
                            genes[gene_id] = gene
                        gene.transcripts.append(transcripts[transcript_name])
                        db.session.add(gene)
                    else:
                        print("Warning: Unkown transcript {0} for gene {1}".format(transcript_name, gene_id))
            db.session.commit()

        # Setup preferred transcript dictonary
        preferred_transcripts = {}  # key = gene, value = transcript
        with open(preferred_transcripts_file, 'r') as f:
            print("Loading preferred transcripts file: {0}".format(preferred_transcripts_file))
            for line in f:
                if not line.startswith('#'):
                    # Parse data
                    data = line.rstrip().split('\t')
                    gene = genes[data[0]]
                    transcript = transcripts[data[1]]

                    # Set default transcript
                    gene.default_transcript = transcript
                    preferred_transcripts[gene.id] = transcript.name
                    db.session.add(gene)
            db.session.commit()

        # Setup gene panel
        with open(gene_panel_file, 'r') as f:
            print("Loading gene panel file: {0}".format(gene_panel_file))
            panels = {}
            for line in f:
                data = line.rstrip().split('\t')
                panel = data[0]

                if 'elid' not in panel:  # Skip old elid panel designs
                    panels[panel] = data[2]

            for panel in sorted(panels.keys()):
                panel_match = re.search('(\w+)v(1\d).(\d)', panel)  # look for [panel_name]v[version] pattern
                genes = panels[panel].split(',')
                if panel_match:
                    panel_name = panel_match.group(1)
                    panel_version_year = panel_match.group(2)
                    panel_version_revision = panel_match.group(3)
                else:
                    panel_name = panel
                    panel_version_year = time.strftime('%y')
                    panel_version_revision = 1

                panel = utils.get_one_or_create(
                    db.session,
                    Panel,
                    name=panel_name,
                )[0]

                panel_version = PanelVersion(panel_name=panel_name, version_year=panel_version_year, version_revision=panel_version_revision, active=True, validated=True, user_id=1)

                for gene in set(genes):
                    if gene in preferred_transcripts:
                        transcript = transcripts[preferred_transcripts[gene]]
                        panel_version.transcripts.append(transcript)
                    else:
                        print("WARNING: Unkown gene: {0}".format(gene))
                db.session.add(panel_version)
            db.session.commit()
