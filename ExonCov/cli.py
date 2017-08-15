"""CLI functions."""

import sys

from flask_script import Command, Option

from . import db, utils
from .models import Gene, Transcript, Exon, SequencingRun, Sample, ExonMeasurement


class LoadDesign(Command):
    """Load design files to database."""

    def __init__(self, default_exon_file='test_files/ENSEMBL_UCSC_merged_collapsed_sorted_v2_20bpflank.bed', default_design_file='test_files/NM_ENSEMBL_HGNC.txt'):
        self.default_exon_file = default_exon_file
        self.default_design_file = default_design_file

    def get_options(self):
        return [
            Option('-e', '--exon_file', dest='exon_file', default=self.default_exon_file),
            Option('-g', '--gene_transcript_file', dest='gene_transcript_file', default=self.default_design_file),
        ]

    def run(self, exon_file, gene_transcript_file):
        """Load design files."""
        print "EXON FILE"
        transcripts = {}
        exons = []
        with open(exon_file, 'r') as f:
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

        print "GENE TRANSCRIPT FILE"
        genes = {}
        with open(gene_transcript_file, 'r') as f:
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
        db.session.close()


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
        else:
            sys.exit("ERROR: Sample and run combination already exists.")

        try:
            f = open(exoncov_file, 'r')
        except IOError:
            sys.exit("ERROR: Can't open file({0}).".format(exoncov_file))
        else:
            with f:
                header = f.readline()
                exon_measurements = []
                measurement_types = header[7:-1]
                for line in f:
                    data = line.rstrip().split('\t')
                    chr, start, end = data[:3]
                    measurements = data[7:-1]

                    for i, measurement in enumerate(measurements):
                        exon_measurement = ExonMeasurement(
                            sample_id=sample.id,
                            exon_id='{}_{}_{}'.format(chr, start, end),
                            measurement=float(measurement),
                            measurement_type=measurement_types[i]
                        )
                        exon_measurements.append(exon_measurement)
                db.session.bulk_save_objects(exon_measurements)
            db.session.commit()
