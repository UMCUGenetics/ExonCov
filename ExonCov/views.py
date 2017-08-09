"""ExonCov views."""

from ExonCov import app

@app.route('/')
def index():
    return 'Hello ExonCov V3!'
