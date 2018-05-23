#!venv/bin/python
"""ExonCov CLI."""
from flask_script import Manager

from flask_security.utils import encrypt_password

from ExonCov import app, db, cli, user_datastore
from ExonCov.models import Role

db_manager = Manager(usage='Database commands.')
manager = Manager(app)


@db_manager.command
def drop():
    """Drop database."""
    db.drop_all()


@db_manager.command
def create():
    """Create database tables."""
    db.create_all()

    # Create admin role and first user
    admin_role = Role(name='admin')
    db.session.add(admin_role)
    db.session.commit()

    user_datastore.create_user(
        first_name='First',
        last_name='Admin',
        email='admin',
        password=encrypt_password('admin'),
        roles=[admin_role]
    )
    db.session.commit()


@db_manager.command
def reset():
    """Reset (drop and create) database tables."""
    drop()
    create()


db_manager.add_command('load_design', cli.LoadDesign())
db_manager.add_command('stats', cli.PrintStats())

manager.add_command("db", db_manager)
manager.add_command('load_sample', cli.LoadSample())


if __name__ == "__main__":
    manager.run()
