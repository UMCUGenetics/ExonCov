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
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
#### Edit config.py
Change the following lines in config.py
```python
SQLALCHEMY_DATABASE_URI = 'mysql://<user>:<password>@localhost/exoncov3' #or 'mysql+mysqlconnector://'
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

### Export and Import existing ExonCov db
Ignore large tables, samples should be imported using cli.
```bash
mysqldump --user=<user> --password --no-data --tab=<dir_name> exoncov

mysqldump --user=<user> --password --no-data --tab=<dir_name> exoncov \
--ignore-table=exoncov.custom_panels \
--ignore-table=exoncov.custom_panels_samples \
--ignore-table=exoncov.custom_panels_transcripts \
--ignore-table=exoncov.sample_projects \
--ignore-table=exoncov.sample_sets \
--ignore-table=exoncov.sample_sets_samples \
--ignore-table=exoncov.samples \
--ignore-table=exoncov.samples_sequencingRun \
--ignore-table=exoncov.sequencing_runs \
--ignore-table=exoncov.transcript_measurements

cat <dir_name>/*.sql > tables.sql
mysql --init-command="SET SESSION FOREIGN_KEY_CHECKS=0;" --user=exoncov --password exoncov < tables.sql
mysql --init-command="SET SESSION FOREIGN_KEY_CHECKS=0;" --user=exoncov --password exoncov
```

Execute following mysql statements to import data from txt files.
```mysql
LOAD DATA LOCAL INFILE 'alembic_version.txt' INTO TABLE alembic_version;
LOAD DATA LOCAL INFILE 'exons.txt' INTO TABLE exons;
LOAD DATA LOCAL INFILE 'exons_transcripts.txt' INTO TABLE exons_transcripts;
LOAD DATA LOCAL INFILE 'gene_aliases.txt' INTO TABLE gene_aliases;
LOAD DATA LOCAL INFILE 'genes.txt' INTO TABLE genes;
LOAD DATA LOCAL INFILE 'panel_versions.txt' INTO TABLE panel_versions;
LOAD DATA LOCAL INFILE 'panels.txt' INTO TABLE panels;
LOAD DATA LOCAL INFILE 'panels_transcripts.txt' INTO TABLE panels_transcripts;
LOAD DATA LOCAL INFILE 'role.txt' INTO TABLE role;
LOAD DATA LOCAL INFILE 'roles_users.txt' INTO TABLE roles_users;
LOAD DATA LOCAL INFILE 'transcripts.txt' INTO TABLE transcripts;
LOAD DATA LOCAL INFILE 'user.txt' INTO TABLE user;
```
