# ExonCov

ExonCov: Exon coverage statistics from BAM files

## Requirements

Exoncov is recommended to be installed with Poetry & pyenv.
It can be installed with PIP, but this is not recommended. 
ExonCov requires Python 3.11 or higher to be present, a MySQL like DB, sambamba and DxTracks to be installed on the system.

### Install MySQL (required database)
https://dev.mysql.com/doc/mysql-installation-excerpt/8.0/en/

### Install sambamba (required binary)
https://github.com/biod/sambamba?tab=readme-ov-file#binary-installation

### Install Dx Tracks (required repository)
https://github.com/UMCUGenetics/Dx_tracks


### Install pyenv (Sets the python version)
https://github.com/pyenv/pyenv?tab=readme-ov-file#installation


### Install Poetry (installs all python requirements)
https://python-poetry.org/docs/#installation

## Setup

```bash
# first set the local python version used (optional, but recommended)
pyenv local 3.11

# Clone git repository
git clone git@github.com:UMCUGenetics/ExonCov.git
cd ExonCov

# Once cloned, install using poetry (excluding non-main dependancies)
poetry install --only main

# Alternative (not recommended)
pip3 install -r requirements.txt
```

#### Edit config.py

Change the following lines in config.py before ExonCov can be used

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
source venv/bin/activate
python ExonCov.py load_design
```

### Import bam file

```bash
source venv/bin/activate
flask --app ExonCov import_bam <project_name> <bam_file>
```

### Run development webserver

```bash
source venv/bin/activate
flask --app ExonCov run --debug
```

### Run production webserver

```bash
source venv/bin/activate
gunicorn -w 4 ExonCov:app
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


## Updating requirements:
To update python packages used, add them to the ```pyproject.toml``` file. 
Here, dependencies can be grouped by type (docs, tests, dev, etc) if desired.

After every update of ```pyproject.toml```, the lock file needs to be updated. To do so, run 
```console
poetry lock
```
to update the ```poetry.lock``` file. 
After these files are updated, make sure to commit both the ```pyproject.toml``` and ```poetry.lock``` to git.
