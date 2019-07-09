# ExonCov
ExonCov: Exon coverage statistics from BAM files

### Requirements
- [Python 2.7](https://www.python.org/)
- [Virtualenv](https://virtualenv.pypa.io/en/stable/)
- [MYSQL](https://www.mysql.com/)
- [sambamba](https://github.com/biod/sambamba)
- [Dx Tracks](https://github.com/UMCUGenetics/Dx_tracks)

### Setup
```bash
# Clone git repository
git clone git@github.com:UMCUGenetics/ExonCov.git
cd ExonCov

# Setup python virtual environment and install python dependencies
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
```
#### Edit config.py
Change the following lines in config.py
```python
SQLALCHEMY_DATABASE_URI = 'mysql://<user>:<password>@localhost/exoncov3'
SECRET_KEY = <generate_key>
SECURITY_PASSWORD_SALT = <generate_salt>

EXON_BED_FILE = 'path/to/Dx_tracks/Tracks/ENSEMBL_UCSC_merged_collapsed_sorted_v3_20bpflank.bed'
GENE_TRANSCRIPT_FILE = 'path/to/Dx_tracks/Exoncov/NM_ENSEMBL_HGNC.txt'
PREFERRED_TRANSCRIPTS_FILE = 'path/to/Dx_tracks/Exoncov/Preferred_transcript_list.txt'
GENE_PANEL_FILE = 'path/to/Dx_tracks/Exoncov/gpanels.txt'

SAMBAMBA = 'path/to/sambamba'

EXON_MEASUREMENTS_RSYNC_PATH = 'rsync/path/for/data'
```

### Load design
```bash
cd /path/to/Exoncov
. venv/bin/activate
python ExonCov.py load_design
```

### Import bam file
```bash
cd /path/to/Exoncov
. venv/bin/activate
python ExonCov.py import_bam <project_name> <bam_file>
```

### Run development webserver
```bash
python ExonCov.py runserver -r -d
```
