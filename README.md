# ExonCov
ExonCov: Exon coverage statistics from BAM files

### Requirements
- [Python 2.7](https://www.python.org/)
- [Virtualenv](https://virtualenv.pypa.io/en/stable/)
- [MYSQL](https://www.mysql.com/)
- [sambamba](https://github.com/biod/sambamba)

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

SAMBAMBA = 'path/to/sambamba'
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
python ExonCov.py import_bam <analysis_name> <bam_file>
```

### Run development webserver
```bash
python ExonCov.py runserver
```
