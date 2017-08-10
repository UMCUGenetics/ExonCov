#!venv/bin/python
"""ExonCov CLI."""
import sys

from flask_script import Manager

from ExonCov import app, db
from ExonCov.models import Gene, Transcript, Exon, SequencingRun, Sample, ExonMeasurement
import ExonCov.utils as utils

db_manager = Manager(usage='Database commands.')
manager = Manager(app)


@db_manager.command
def drop():
    """Drop database."""
    db.drop_all()


@db_manager.command
def create():
    """Create database."""
    db.create_all()


@db_manager.command
def reset():
    """Reset (drop and create) database."""
    drop()
    create()


@db_manager.command
def load_design(
    exon_file='design_files/ENSEMBL_UCSC_merged_collapsed_sorted_v2_20bpflank.bed',
    gene_transcript_file='design_files/NM_ENSEMBL_HGNC.txt'
):
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


manager.add_command("db", db_manager)


@manager.command
def load_sample(run_name, sample_name, exoncov_file):
    """Load sample data."""
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


if __name__ == "__main__":
    manager.run()
