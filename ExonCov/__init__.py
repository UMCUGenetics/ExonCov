"""ExonCov flask app."""
from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import flask_admin
from flask_security import Security, SQLAlchemyUserDatastore
from flask_debugtoolbar import DebugToolbarExtension


from utils import url_for_other_page, event_logger

# Setup APP
app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
admin = flask_admin.Admin(app, name='ExonCov Admin', template_mode='bootstrap3')

# Debug
toolbar = DebugToolbarExtension(app)

app.jinja_env.globals['url_for_other_page'] = url_for_other_page

from . import views, admin_views, models, forms

# Setup flask_security
user_datastore = SQLAlchemyUserDatastore(db, models.User, models.Role)
security = Security(app, user_datastore, register_form=forms.ExtendedRegisterForm)
security.login_manager.session_protection = 'strong'


@security.context_processor
def security_context_processor():
    """Merge flask-admin's template context into the flask-security views."""
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=flask_admin.helpers,
        get_url=url_for
    )


@db.event.listens_for(models.Panel, "after_insert")
@db.event.listens_for(models.PanelVersion, "after_insert")
def after_update(mapper, connection, target):
    event_data = dict(target.__dict__)
    event_logger(connection, models.EventLog, target.__class__.__name__, 'insert', event_data)


@db.event.listens_for(models.Panel, "after_update")
@db.event.listens_for(models.PanelVersion, "after_update")
def after_insert(mapper, connection, target):
    event_data = dict(target.__dict__)
    event_logger(connection, models.EventLog, target.__class__.__name__, 'update', event_data)
