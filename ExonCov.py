#!venv/bin/python
"""ExonCov CLI."""
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from ExonCov import app, db, cli

manager = Manager(app)
migrate = Migrate(app, db)
db_manager = Manager(usage='Database commands.')

manager.add_command("db", db_manager)
manager.add_command('import_bam', cli.ImportBam())
manager.add_command('search_sample', cli.SearchSample())
manager.add_command('remove_sample', cli.RemoveSample())
manager.add_command('check_samples', cli.CheckSamples())

db_manager.add_command('migrate', MigrateCommand)
db_manager.add_command('stats', cli.PrintStats())
db_manager.add_command('panel_genes', cli.PrintPanelGenesTable())
db_manager.add_command('import_alias_table', cli.ImportAliasTable())
db_manager.add_command('export_panel_bed', cli.PrintPanelBed())
#db_manager.add_command('load_design', cli.LoadDesign())

if __name__ == "__main__":
    manager.run()
