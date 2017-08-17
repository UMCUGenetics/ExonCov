"""ExonCov SQLAlchemy database models."""

import datetime

from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.ext.hybrid import hybrid_property

from . import db

# association tables
exons_transcripts = db.Table(
    'exons_transcripts',
    db.Column('exon_id', db.ForeignKey('exons.id'), primary_key=True),
    db.Column('transcript_id', db.ForeignKey('transcripts.id'), primary_key=True)
)


class Exon(db.Model):
    """Exon class."""

    __tablename__ = 'exons'

    id = db.Column(db.String(25), primary_key=True)  # chr_start_end
    chr = db.Column(db.String(2))
    start = db.Column(db.Integer)
    end = db.Column(db.Integer)

    transcripts = db.relationship('Transcript', secondary=exons_transcripts, back_populates='exons')
    exon_measurements = db.relationship('ExonMeasurement', back_populates='exon')

    def __repr__(self):
        return "Exon({0}:{1}-{2})".format(self.chr, self.start, self.end)

    @hybrid_property
    def len(self):
        return self.end - self.start


class Transcript(db.Model):
    """Transcript class."""

    __tablename__ = 'transcripts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True, unique=True)

    gene_id = db.Column(db.Integer, db.ForeignKey('genes.id'))

    exons = db.relationship('Exon', secondary=exons_transcripts, back_populates='transcripts')
    gene = db.relationship('Gene', back_populates='transcripts')

    def __repr__(self):
        return "Transcript({0})".format(self.name)


class Gene(db.Model):
    """Gene class."""

    __tablename__ = 'genes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True, unique=True)  # hgnc

    transcripts = db.relationship('Transcript', back_populates='gene')

    def __repr__(self):
        return "Gene({0})".format(self.name)


class Sample(db.Model):
    """Sample class."""

    __tablename__ = 'samples'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True)
    import_date = db.Column(db.Date, default=datetime.datetime.today)

    sequencing_run_id = db.Column(db.Integer, db.ForeignKey('sequencing_runs.id'))

    sequencing_run = db.relationship('SequencingRun', back_populates='samples')
    exon_measurements = db.relationship('ExonMeasurement', back_populates='sample')

    __table_args__ = (
        UniqueConstraint('name', 'sequencing_run_id'),
        Index('sample_run', 'name', 'sequencing_run_id')
    )


    def __repr__(self):
        return "Sample({0})".format(self.name)


class SequencingRun(db.Model):
    """Sample class."""

    __tablename__ = 'sequencing_runs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True)

    samples = db.relationship('Sample', back_populates='sequencing_run')

    def __repr__(self):
        return "SequencingRun({0})".format(self.name)


class ExonMeasurement(db.Model):
    """Exon measurement class, stores sample (coverage) measurements per exon."""

    __tablename__ = 'exon_measurements'

    id = db.Column(db.Integer, primary_key=True)
    measurement = db.Column(db.Float)
    measurement_type = db.Column(db.String(25), index=True)  # e.g. percentage20

    exon_id = db.Column(db.String(25), db.ForeignKey('exons.id'))
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'))

    sample = db.relationship('Sample', back_populates='exon_measurements')
    exon = db.relationship('Exon', back_populates='exon_measurements')

    __table_args = (
        UniqueConstraint('exon_id', 'sample_id', 'measurement_type')
    )

    def __repr__(self):
        return "ExonMeasurement({0}-{1}-{2})".format(self.measurement_type, self.sample, self.exon)
