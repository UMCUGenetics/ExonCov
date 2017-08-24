"""CLI functions."""

import sys

from flask_script import Command, Option

from . import db, utils
from .models import Gene, Transcript, Exon, SequencingRun, Sample, ExonMeasurement, Panel


class LoadDesign(Command):
    """Load design files to database."""

    def __init__(
        self,
        default_exon_file='test_files/ENSEMBL_UCSC_merged_collapsed_sorted_v2_20bpflank.bed',
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
                transcript_data = set(data[6].split(':'))

                # Create exon
                exon = Exon(
                    id='{}_{}_{}'.format(chr, start, end),
                    chr=chr,
                    start=int(start),
                    end=int(end)
                )

                # Create transcripts
                for transcript_name in transcript_data:

                    if transcript_name in transcripts:
                        transcript = transcripts[transcript_name]
                    else:
                        transcript = Transcript(name=transcript_name)
                        transcripts[transcript_name] = transcript
                    exon.transcripts.append(transcript)
                exons.append(exon)

            db.session.add_all(exons)
            db.session.add_all(transcripts.values())

        db.session.commit()

        # Load gene and transcript file
        genes = {}
        with open(gene_transcript_file, 'r') as f:
            print "Loading gene transcript file: {0}".format(gene_transcript_file)
            for line in f:
                if line.startswith('#'):
                    continue

                data = line.rstrip().split('\t')
                gene_name = data[0]
                transcript_name = data[1]
                if gene_name in genes:
                    gene = genes[gene_name]
                else:
                    gene = Gene(name=data[0])
                if transcript_name in transcripts:
                    gene.transcripts.append(transcripts[transcript_name])
                genes[gene_name] = gene

            db.session.add_all(genes.values())

        db.session.commit()

        # Setup preferred transcript dictonary
        preferred_transcripts = {}  # key = gene, value = transcript
        with open(preferred_transcripts_file, 'r') as f:
            print "Loading preferred transcripts file: {0}".format(preferred_transcripts_file)
            for line in f:
                if line.startswith('#'):
                    continue
                data = line.rstrip().split('\t')
                preferred_transcripts[data[1]] = data[0]

        # Setup gene panel
        with open(gene_panel_file, 'r') as f:
            print "Loading gene panel file: {0}".format(gene_panel_file)
            f.readline()  # skip header
            for line in f:
                data = line.rstrip().split('\t')
                panel_name = data[0]
                genes = data[2].split(',')

                panel = Panel(name=panel_name)

                for gene in set(genes):
                    transcript = transcripts[preferred_transcripts[gene]]
                    panel.transcripts.append(transcript)
                db.session.add(panel)
            db.session.commit()


class LoadSample(Command):
    """Load sample from exoncov file."""

    option_list = (
        Option('run_name'),
        Option('sample_name'),
        Option('exoncov_file'),
    )

    def run(self, run_name, sample_name, exoncov_file):
        """Run function."""
        sequencing_run = utils.get_one_or_create(
            db.session,
            SequencingRun,
            name=run_name
        )[0]  # returns object and exists bool

        sample = Sample.query.filter_by(name=sample_name).filter_by(sequencing_run=sequencing_run).first()
        if not sample:
            sample = Sample(name=sample_name, sequencing_run=sequencing_run)
            db.session.add(sample)
            db.session.commit()
        else:
            sys.exit("ERROR: Sample and run combination already exists.")

        try:
            f = open(exoncov_file, 'r')
        except IOError:
            sys.exit("ERROR: Can't open file({0}).".format(exoncov_file))
        else:
            with f:
                print "Loading sample: {0}-{1}-{2}".format(run_name, sample_name, exoncov_file)
                header = f.readline().rstrip().split('\t')
                exon_measurements = []
                measurement_types = header[7:-1]

                for line in f:
                    data = line.rstrip().split('\t')
                    chr, start, end = data[:3]
                    measurements = data[7:-1]

                    exon_measurements.extend(
                        [
                            dict(
                                sample_id=sample.id, exon_id='{}_{}_{}'.format(chr, start, end),
                                measurement=float(measurement), measurement_type=measurement_types[i]
                            )
                            for i, measurement in enumerate(measurements)
                        ]
                    )
                db.session.bulk_insert_mappings(ExonMeasurement, exon_measurements)
            db.session.commit()


class PrintStats(Command):
    """Print database stats."""

    def run(self):
        """Run function."""
        print "Number of genes: {0}".format(Gene.query.count())
        print "Number of transcripts: {0}".format(Transcript.query.count())
        print "Number of exons: {0}".format(Exon.query.count())
        print "Number of panels: {0}".format(Panel.query.count())
        print "Number of samples: {0}".format(Sample.query.count())
