"""ExonCov wsgi."""
activate_this = '/var/www/html/exoncov3/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

# Add app to the path
import sys
sys.path.insert(0, "/var/www/html/exoncov3")

# Load app
from ExonCov import app as application
from ExonCov.utils import WSGIMiddleware

# Setup prefix
application.wsgi_app = WSGIMiddleware(application.wsgi_app, "/exoncov3")
