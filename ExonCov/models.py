"""ExonCov SQLAlchemy database models."""

import datetime

from flask_security import UserMixin, RoleMixin
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
    db.Column('panel_id', db.ForeignKey('panel_versions.id'), primary_key=True),
    db.Column('transcript_id', db.ForeignKey('transcripts.id'), primary_key=True)
)

roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'))
)

samples_sequencingRun = db.Table(
    'samples_sequencingRun',
    db.Column('sample_id', db.Integer, db.ForeignKey('samples.id')),
    db.Column('sequencingRun_id', db.Integer, db.ForeignKey('sequencing_runs.id'))
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

    def __str__(self):
        return "{0}:{1}-{2}".format(self.chr, self.start, self.end)

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

    exons = db.relationship('Exon', secondary=exons_transcripts, back_populates='transcripts')
    gene = db.relationship('Gene', backref='transcripts', foreign_keys=[gene_id], lazy='joined')  # Why backref?
    panels = db.relationship('PanelVersion', secondary=panels_transcripts, back_populates='transcripts')
    transcript_measurements = db.relationship('TranscriptMeasurement', back_populates='transcript')

    def __repr__(self):
        return "Transcript({0})".format(self.name)

    def __str__(self):
        return self.name

    @hybrid_property
    def exon_count(self):
        """Count number of exons."""
        return len(self.exons)


class Gene(db.Model):
    """Gene class."""

    __tablename__ = 'genes'

    id = db.Column(db.String(50, collation='utf8_bin'), primary_key=True)  # hgnc
    default_transcript_id = db.Column(db.Integer, db.ForeignKey('transcripts.id', name='default_transcript_foreign_key'), index=True)

    default_transcript = db.relationship('Transcript', foreign_keys=[default_transcript_id])

    def __repr__(self):
        return "Gene({0})".format(self.id)

    def __str__(self):
        return self.id


class Panel(db.Model):
    """Panel class."""

    __tablename__ = 'panels'

    name = db.Column(db.String(50), primary_key=True)

    versions = db.relationship('PanelVersion', back_populates='panel', order_by="PanelVersion.id")

    def __repr__(self):
        return "Panel({0})".format(self.name)

    def __str__(self):
        return "{0}".format(self.name)

    @hybrid_property
    def last_version(self):
        return self.versions[-1]


class PanelVersion(db.Model):
    """Panel version class."""

    __tablename__ = 'panel_versions'

    id = db.Column(db.Integer, primary_key=True)
    version_year = db.Column(db.Integer, index=True)
    version_revision = db.Column(db.Integer, index=True)
    active = db.Column(db.Boolean, index=True, default=False)
    validated = db.Column(db.Boolean, index=True, default=False)
    panel_name = db.Column(db.String(50), db.ForeignKey('panels.name'), index=True)

    panel = db.relationship('Panel', back_populates='versions')
    transcripts = db.relationship('Transcript', secondary=panels_transcripts, back_populates='panels', lazy='joined')  # TODO Check query speed!

    def __repr__(self):
        return "PanelVersion({0})".format(self.name_version)

    def __str__(self):
        return "{0}".format(self.name_version)

    @hybrid_property
    def version(self):
        """Return version."""
        return "{0}.{1}".format(self.version_year, self.version_revision)

    @hybrid_property
    def name_version(self):
        """Return panel and version."""
        return "{0}v{1}".format(self.panel_name, self.version)

    @hybrid_property
    def gene_count(self):
        """Calculate number of genes."""
        return len(self.transcripts)


class Sample(db.Model):
    """Sample class."""

    __tablename__ = 'samples'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), index=True)
    import_date = db.Column(db.Date, default=datetime.date.today, index=True)
    file_name = db.Column(db.String(255))

    exon_measurements = db.relationship('ExonMeasurement', cascade="all,delete", back_populates='sample')
    transcript_measurements = db.relationship('TranscriptMeasurement', cascade="all,delete", back_populates='sample')
    sequencing_runs = db.relationship(
        'SequencingRun', secondary=samples_sequencingRun,
        backref=db.backref('samples', lazy='joined')
    )

    # __table_args__ = (
    #     UniqueConstraint('name', 'sequencing_run_id'),
    #     Index('sample_run', 'name', 'sequencing_run_id')
    # )

    def __repr__(self):
        return "Sample({0})".format(self.name)

    def __str__(self):
        return self.name


class SequencingRun(db.Model):
    """Sequencing run class."""

    __tablename__ = 'sequencing_runs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True)
    sequencer = db.Column(db.String(50), index=True)

    def __repr__(self):
        return "SequencingRun({0})".format(self.name)

    def __str__(self):
        return self.name


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


class User(db.Model, UserMixin):
    """User model."""

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean(), index=True, nullable=False)

    roles = db.relationship(
        'Role', secondary=roles_users,
        backref=db.backref('users', lazy='dynamic')
    )

    def __init__(self, email, password, first_name, last_name, active, roles):
        self.email = email
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.active = False
        self.roles = roles

    def __repr__(self):
        return "User({0}-{1})".format(self.id, self.email)

    def __str__(self):
        """Return string representation."""
        return self.email

    @hybrid_property
    def name_email(self):
        """Return full name and email."""
        return "{0} {1} ({2})".format(
            self.first_name,
            self.last_name,
            self.email
        )


class Role(db.Model, RoleMixin):
    """Role model."""

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return "Role({0}-{1})".format(self.id, self.name)

    def __str__(self):
        """Return string representation."""
        return self.name
