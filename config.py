"""ExonCov configuration."""

# SQLAlchemy
SQLALCHEMY_DATABASE_URI = 'mysql://exoncov3:exoncov3@localhost/exoncov3'
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = False

# FlaskForm
SECRET_KEY = 'change_this'

# Flask-Security
SECURITY_PASSWORD_HASH = 'pbkdf2_sha512'
SECURITY_PASSWORD_SALT = 'change_this'

SECURITY_LOGIN_URL = '/login/'
SECURITY_LOGOUT_URL = '/logout/'
SECURITY_REGISTER_URL = '/register/'
SECURITY_POST_LOGIN_VIEW = '/'
SECURITY_POST_LOGOUT_VIEW = '/'

SECURITY_REGISTERABLE = True
SECURITY_CHANGEABLE = True
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False

SECURITY_MSG_DISABLED_ACCOUNT = ('Please contact admins to activate your account.', 'error')

# JINJA template
TEMPLATES_AUTO_RELOAD = True

# Debug toolbar
DEBUG_TB_ENABLED = True
DEBUG_TB_PROFILER_ENABLED = False
DEBUG_TB_INTERCEPT_REDIRECTS = False

# Exon, Transcript, Gene, Panel files
EXON_BED_FILE = 'Dx_tracks/Tracks/ENSEMBL_UCSC_merged_collapsed_sorted_v3_20bpflank.bed'
GENE_TRANSCRIPT_FILE = 'Dx_tracks/Exoncov/NM_ENSEMBL_HGNC.txt'
PREFERRED_TRANSCRIPTS_FILE = 'Dx_tracks/Exoncov/Preferred_transcript_list.txt'
GENE_PANEL_FILE = 'Dx_tracks/Exoncov/gpanels.txt'

# Sambamba count settings
SAMBAMBA = 'test_files/sambamba_v0.6.6'
SAMBAMBA_THREADS = 4
SAMBAMBA_FILTER = 'mapping_quality >= 20 and not duplicate and not failed_quality_control and not secondary_alignment'
