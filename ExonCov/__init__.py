"""ExonCov flask app."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_admin import Admin
from flask_debugtoolbar import DebugToolbarExtension

from utils import url_for_other_page

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
admin = Admin(app, name='ExonCov Admin', template_mode='bootstrap3')

# Debug
toolbar = DebugToolbarExtension(app)

app.jinja_env.globals['url_for_other_page'] = url_for_other_page

from . import views, admin_views, models
