"""CLI functions."""

import sys
import re
import time
import subprocess
import shlex

from flask_script import Command, Option
from flask_security.utils import encrypt_password
from sqlalchemy import func
import pysam

from . import app, db, utils, user_datastore
from .models import Role, Gene, Transcript, Exon, SequencingRun, Sample, samples_sequencingRun, ExonMeasurement, TranscriptMeasurement, Panel, PanelVersion, CustomPanel
from .utils import weighted_average

# DB CLI
class Drop(Command):
    """Drop database."""

    def run(self):
        db.drop_all()


class Create(Command):
    """Create database tables."""

    def run(self):
        db.create_all()

        # Create admin role and first user
        site_admin_role = Role(name='site_admin')
        db.session.add(site_admin_role)
        panel_admin_role = Role(name='panel_admin')
        db.session.add(panel_admin_role)

        db.session.commit()

        admin = user_datastore.create_user(
            first_name='First',
            last_name='Admin',
            email='admin@admin.nl',
            password=encrypt_password('admin'),
            active=True,
            roles=[site_admin_role, panel_admin_role]
        )
        admin.active = True
        db.session.add(admin)
        db.session.commit()


class Reset(Command):
    """Reset (drop and create) database tables."""

    def run(self):
        drop = Drop()
        drop.run()

        create = Create()
        create.run()


class PrintStats(Command):
    """Print database stats."""

    def run(self):
        """Run function."""
        print "Number of genes: {0}".format(Gene.query.count())
        print "Number of transcripts: {0}".format(Transcript.query.count())
        print "Number of exons: {0}".format(Exon.query.count())
        print "Number of panels: {0}".format(Panel.query.count())
        print "Number of custom panels: {0}".format(CustomPanel.query.count())
        print "Number of samples: {0}".format(Sample.query.count())


class LoadDesign(Command):
    """Load design files to database."""

    def __init__(
        self,
        default_exon_file='test_files/ENSEMBL_UCSC_merged_collapsed_sorted_v2_20bpflank.multi_chr_transcripts_removed.bed',
        default_gene_transcript_file='test_files/NM_ENSEMBL_HGNC.txt',
        default_preferred_transcripts_file='test_files/preferred_transcripts.txt',
        defaut_gene_panel_file='test_files/gpanels.txt',
    ):
        self.default_exon_file = default_exon_file
        self.default_gene_transcript_file = default_gene_transcript_file
        self.default_preferred_transcripts_file = default_preferred_transcripts_file
        self.defaut_gene_panel_file = defaut_gene_panel_file

    def get_options(self):
        return [
            Option('-e', '--exon_file', dest='exon_file', default=self.default_exon_file),
            Option('-gt', '--gene_transcript', dest='gene_transcript_file', default=self.default_gene_transcript_file),
            Option('-pt', '--preferred_transcripts', dest='preferred_transcripts_file', default=self.default_preferred_transcripts_file),
            Option('-gp', '--gene_panel', dest='gene_panel_file', default=self.defaut_gene_panel_file),
        ]

    def run(self, exon_file, gene_transcript_file, preferred_transcripts_file, gene_panel_file):
        """Load files."""
        transcripts = {}
        exons = []
        # Parse Exon file
        with open(exon_file, 'r') as f:
            print "Loading exon file: {0}".format(exon_file)
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
                    print "Warning: No transcripts for exon: {0}.".format(exon)
                    transcript_data = []

                # Create transcripts
                for transcript_name in transcript_data:

                    if transcript_name in transcripts:
                        transcript = transcripts[transcript_name]

                        # Set start / end positions
                        if transcript.start > exon.start:
                            transcript.start = exon.start
                        if transcript.end < exon.end:
                            transcript.end = exon.end

                        # Sanity check chromosome
                        if transcript.chr != exon.chr:
                            print "Warning: Different chromosomes for {0} and {1}".format(transcript, exon)

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
            print "Loading gene transcript file: {0}".format(gene_transcript_file)
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
                        print "Warning: Unkown transcript {0} for gene {1}".format(transcript_name, gene.id)
            db.session.commit()

        # Setup preferred transcript dictonary
        preferred_transcripts = {}  # key = gene, value = transcript
        with open(preferred_transcripts_file, 'r') as f:
            print "Loading preferred transcripts file: {0}".format(preferred_transcripts_file)
            for line in f:
                if not line.startswith('#'):
                    # Parse data
                    data = line.rstrip().split('\t')
                    transcript = transcripts[data[0]]
                    gene = genes[data[1]]

                    # Set default transcript
                    gene.default_transcript = transcript
                    preferred_transcripts[gene.id] = transcript.name
                    db.session.add(gene)
            db.session.commit()

        # Setup gene panel
        with open(gene_panel_file, 'r') as f:
            print "Loading gene panel file: {0}".format(gene_panel_file)
            f.readline()  # skip header
            for line in f:
                data = line.rstrip().split('\t')
                panel = data[0]

                if 'elid' not in panel:  # Skip old elid panel designs
                    panel_match = re.search('(\w+)v(1\d).(\d)', panel)  # look for [panel_name]v[version] pattern
                    if panel_match:
                        panel_name = panel_match.group(1)
                        panel_version_year = panel_match.group(2)
                        panel_version_revision = panel_match.group(3)
                    else:
                        panel_name = panel
                        panel_version_year = time.strftime('%y')
                        panel_version_revision = 1

                    genes = data[2].split(',')

                    panel = utils.get_one_or_create(
                        db.session,
                        Panel,
                        name=panel_name,
                    )[0]

                    panel_version = PanelVersion(panel_name=panel_name, version_year=panel_version_year, version_revision=panel_version_revision, active=True, validated=True)

                    for gene in set(genes):
                        transcript = transcripts[preferred_transcripts[gene]]
                        panel_version.transcripts.append(transcript)
                    db.session.add(panel_version)
            db.session.commit()


# Sample CLI
class ImportBam(Command):
    """Import sample from bam file."""

    option_list = (
        Option('bam'),
        Option('-r', '--sequencing_run_name', dest='sequencing_run_name'),
        Option('-o', '--overwrite', dest='overwrite', default=False, action='store_true'),
        Option('-p', '--print_output', dest='print_output', default=False, action='store_true')
    )

    def run(self, bam, sequencing_run_name, overwrite=False, print_output=False):
        try:
            bam_file = pysam.AlignmentFile(bam, "rb")
        except IOError as e:
            sys.exit(e)

        sample_name = None
        sequencing_runs = {}
        sequencing_run_ids = []
        exon_measurements = []

        # Parse read groups
        for read_group in bam_file.header['RG']:
            if not sample_name:
                sample_name = read_group['SM']
            elif sample_name != read_group['SM']:
                sys.exit("Exoncov does not support bam files containing multiple samples.")

            if read_group['PU'] not in sequencing_runs:
                if sequencing_run_name:
                    sequencing_run, sequencing_run_exists = utils.get_one_or_create(
                        db.session,
                        SequencingRun,
                        name=sequencing_run_name,
                        platform_unit=read_group['PU']
                    )  # returns object and exists bool
                else:
                    sequencing_run, sequencing_run_exists = utils.get_one_or_create(
                        db.session,
                        SequencingRun,
                        name=read_group['PU'],
                        platform_unit=read_group['PU']
                    )  # returns object and exists bool

                sequencing_runs[read_group['PU']] = sequencing_run
                sequencing_run_ids.append(sequencing_run.id)
        bam_file.close()

        # Look for sample in database
        sample = Sample.query.filter_by(name=sample_name).join(samples_sequencingRun).filter(SequencingRun.id.in_(sequencing_run_ids)).group_by(Sample).having(len(sequencing_run_ids) == func.count(samples_sequencingRun.c.sequencingRun_id)).first()

        if sample and overwrite:
            db.session.delete(sample)
            db.session.commit()

        elif sample and not overwrite:
            sys.exit("ERROR: Sample and run(s) combination already exists.")

        # Create sample
        sample = Sample(name=sample_name, file_name=bam, sequencing_runs=sequencing_runs.values())
        db.session.add(sample)
        db.session.commit()

        # Run sambamba
        sambamba_command = "{sambamba} depth region {bam_file} --nthreads {threads} --fix-mate-overlaps --min-base-quality 10 --filter '{filter}' --regions {bed_file} {cov_threshold_settings}".format(
            sambamba=app.config['SAMBAMBA'],
            bam_file=bam,
            threads=app.config['SAMBAMBA_THREADS'],
            filter=app.config['SAMBAMBA_FILTER'],
            bed_file=app.config['SAMBAMBA_BED'],
            cov_threshold_settings='--cov-threshold 10 --cov-threshold 15 --cov-threshold 20 --cov-threshold 30 --cov-threshold 50 --cov-threshold 100',
        )
        p = subprocess.Popen(shlex.split(sambamba_command), stdout=subprocess.PIPE)

        for line in p.stdout:
            if print_output:
                print line

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

            # Measurement
            else:
                data = line.rstrip().split('\t')
                chr, start, end = data[:3]
                measurement_mean_coverage = data[measurement_mean_coverage_index]
                measurement_percentage10 = data[measurement_percentage10_index]
                measurement_percentage15 = data[measurement_percentage15_index]
                measurement_percentage20 = data[measurement_percentage20_index]
                measurement_percentage30 = data[measurement_percentage30_index]
                measurement_percentage50 = data[measurement_percentage50_index]
                measurement_percentage100 = data[measurement_percentage100_index]

                exon_measurements.append({
                    'sample_id': sample.id,
                    'exon_id': '{0}_{1}_{2}'.format(chr, start, end),
                    'measurement_mean_coverage': measurement_mean_coverage,
                    'measurement_percentage10': measurement_percentage10,
                    'measurement_percentage15': measurement_percentage15,
                    'measurement_percentage20': measurement_percentage20,
                    'measurement_percentage30': measurement_percentage30,
                    'measurement_percentage50': measurement_percentage50,
                    'measurement_percentage100': measurement_percentage100,
                })

        # Bulk insert exons measurements
        bulk_insert_n = 5000
        for i in range(0, len(exon_measurements), bulk_insert_n):
            db.session.bulk_insert_mappings(ExonMeasurement, exon_measurements[i:i+bulk_insert_n])
            db.session.commit()

        # Set transcript measurements
        query = db.session.query(Transcript.id, Exon.len, ExonMeasurement).join(Exon, Transcript.exons).join(ExonMeasurement).filter_by(sample_id=sample.id).all()
        transcripts = {}

        for transcript_id, exon_len, exon_measurement in query:
            if transcript_id not in transcripts:
                transcripts[transcript_id] = {
                    'len': exon_len,
                    'transcript_id': transcript_id,
                    'sample_id': sample.id,
                    'measurement_mean_coverage': exon_measurement.measurement_mean_coverage,
                    'measurement_percentage10': exon_measurement.measurement_percentage10,
                    'measurement_percentage15': exon_measurement.measurement_percentage15,
                    'measurement_percentage20': exon_measurement.measurement_percentage20,
                    'measurement_percentage30': exon_measurement.measurement_percentage30,
                    'measurement_percentage50': exon_measurement.measurement_percentage50,
                    'measurement_percentage100': exon_measurement.measurement_percentage100,
                }
            else:
                measurement_types = ['measurement_mean_coverage', 'measurement_percentage10', 'measurement_percentage15', 'measurement_percentage20', 'measurement_percentage30', 'measurement_percentage50', 'measurement_percentage100']
                for measurement_type in measurement_types:
                    transcripts[transcript_id][measurement_type] = weighted_average(
                        [transcripts[transcript_id][measurement_type], exon_measurement[measurement_type]],
                        [transcripts[transcript_id]['len'], exon_len]
                    )
                transcripts[transcript_id]['len'] += exon_len

        # Bulk insert transcript measurements
        bulk_insert_n = 5000
        transcript_values = transcripts.values()
        for i in range(0, len(transcript_values), bulk_insert_n):
            db.session.bulk_insert_mappings(TranscriptMeasurement, transcript_values[i:i+bulk_insert_n])
            db.session.commit()


class SearchSample(Command):
    """Search sample in database."""

    option_list = (
        Option('sample_name'),
    )

    def run(self, sample_name):
        samples = Sample.query.filter_by(name=sample_name).all()

        print "Sample ID\tSample Name\tSequencing Runs\tCustom Panels"
        for sample in samples:
            print "{id}\t{name}\t{runs}\t{custom_panels}".format(
                id=sample.id,
                name=sample.name,
                runs=sample.sequencing_runs,
                custom_panels=sample.custom_panels,
            )


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
