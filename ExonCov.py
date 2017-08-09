#!venv/bin/python
"""ExonCov CLI."""
from flask_script import Manager

from ExonCov import app, db

db_manager = Manager(usage='Database commands.')


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


manager = Manager(app)
manager.add_command("db", db_manager)

if __name__ == "__main__":
    manager.run()
