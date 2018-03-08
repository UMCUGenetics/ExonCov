"""ExonCov SQLAlchemy database models."""

import datetime

from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.mysql import BIGINT

from . import db

# association tables
exons_transcripts = db.Table(
    'exons_transcripts',
    db.Column('exon_id', db.ForeignKey('exons.id'), primary_key=True),
    db.Column('transcript_id', db.ForeignKey('transcripts.id'), primary_key=True)
)

panels_transcripts = db.Table(
    'panels_transcripts',
    db.Column('panel_id', db.ForeignKey('panels.id'), primary_key=True),
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
        """Calculate exon length."""
        return self.end - self.start


class Transcript(db.Model):
    """Transcript class."""

    __tablename__ = 'transcripts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True, unique=True)
    chr = db.Column(db.String(2))  # Based on exon.chr
    start = db.Column(db.Integer)  # Based on smallest exon.start
    end = db.Column(db.Integer)  # Based on largest exon.end

    gene_id = db.Column(db.String(50, collation='utf8_bin'), db.ForeignKey('genes.id'), index=True)

    exons = db.relationship('Exon', secondary=exons_transcripts, back_populates='transcripts', lazy='joined')
    gene = db.relationship('Gene', backref='transcripts', foreign_keys=[gene_id], lazy='joined')
    panels = db.relationship('Panel', secondary=panels_transcripts, back_populates='transcripts')
    transcript_measurements = db.relationship('TranscriptMeasurement', back_populates='transcript')

    def __repr__(self):
        return "Transcript({0})".format(self.name)

    @hybrid_property
    def exon_count(self):
        """Count number of exons."""
        return len(self.exons)


class Gene(db.Model):
    """Gene class."""

    __tablename__ = 'genes'

    id = db.Column(db.String(50, collation='utf8_bin'), primary_key=True)  # hgnc
    default_transcript_id = db.Column(db.Integer, db.ForeignKey('transcripts.id', name='default_transcript_foreign_key'), index=True)

    #transcripts = db.relationship('Transcript', back_populates='gene')
    default_transcript = db.relationship('Transcript', foreign_keys=[default_transcript_id])

    def __repr__(self):
        return "Gene({0})".format(self.id)


class Panel(db.Model):
    """Panel class."""

    __tablename__ = 'panels'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True, unique=True)

    transcripts = db.relationship('Transcript', secondary=panels_transcripts, back_populates='panels')

    def __repr__(self):
        return "Panel({0})".format(self.name)

    @hybrid_property
    def gene_count(self):
        """Calculate number of genes."""
        return len(self.transcripts)


class Sample(db.Model):
    """Sample class."""

    __tablename__ = 'samples'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True)
    import_date = db.Column(db.Date, default=datetime.date.today)
    sequencing_run_id = db.Column(db.Integer, db.ForeignKey('sequencing_runs.id'), index=True)

    sequencing_run = db.relationship('SequencingRun', back_populates='samples', lazy='joined')
    exon_measurements = db.relationship('ExonMeasurement', back_populates='sample')
    transcript_measurements = db.relationship('TranscriptMeasurement', back_populates='sample')

    __table_args__ = (
        UniqueConstraint('name', 'sequencing_run_id'),
        Index('sample_run', 'name', 'sequencing_run_id')
    )

    def __repr__(self):
        return "Sample({0})".format(self.name)


class SequencingRun(db.Model):
    """Sequencing run class."""

    __tablename__ = 'sequencing_runs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True)

    samples = db.relationship('Sample', back_populates='sequencing_run')

    def __repr__(self):
        return "SequencingRun({0})".format(self.name)


class ExonMeasurement(db.Model):
    """Exon measurement class, stores sample measurements per exon."""

    __tablename__ = 'exon_measurements'

    id = db.Column(BIGINT(unsigned=True), primary_key=True)

    measurement_mean_coverage = db.Column(db.Float)
    measurement_percentage10 = db.Column(db.Float)
    measurement_percentage15 = db.Column(db.Float)
    measurement_percentage20 = db.Column(db.Float)
    measurement_percentage30 = db.Column(db.Float)
    measurement_percentage50 = db.Column(db.Float)
    measurement_percentage100 = db.Column(db.Float)

    exon_id = db.Column(db.String(25), db.ForeignKey('exons.id'), index=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'), index=True)

    sample = db.relationship('Sample', back_populates='exon_measurements')
    exon = db.relationship('Exon', back_populates='exon_measurements')

    __table_args = (
        UniqueConstraint('exon_id', 'sample_id')
    )

    def __repr__(self):
        return "ExonMeasurement({0}-{1})".format(self.sample, self.exon)

    def __getitem__(self, item):
        return getattr(self, item)


class TranscriptMeasurement(db.Model):
    """Transcript measurement class, stores sample measurements per transcript."""

    __tablename__ = 'transcript_measurements'

    id = db.Column(BIGINT(unsigned=True), primary_key=True)
    len = db.Column(db.Integer)  # Store length used to calculate weighted average
    measurement_mean_coverage = db.Column(db.Float)
    measurement_percentage10 = db.Column(db.Float)
    measurement_percentage15 = db.Column(db.Float)
    measurement_percentage20 = db.Column(db.Float)
    measurement_percentage30 = db.Column(db.Float)
    measurement_percentage50 = db.Column(db.Float)
    measurement_percentage100 = db.Column(db.Float)

    transcript_id = db.Column(db.Integer, db.ForeignKey('transcripts.id'), index=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'), index=True)

    sample = db.relationship('Sample', back_populates='transcript_measurements')
    transcript = db.relationship('Transcript', back_populates='transcript_measurements')

    __table_args = (
        UniqueConstraint('transcript_id', 'sample_id')
    )

    def __repr__(self):
        return "TranscriptMeasurement({0}-{1})".format(self.sample, self.transcript)

    def __getitem__(self, item):
        return getattr(self, item)
