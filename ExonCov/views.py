"""ExonCov views."""

from flask import render_template

from ExonCov import app
from .models import Sample


@app.route('/')
@app.route('/sample')
def samples():
    """Sample overview page."""
    samples = Sample.query.all()
    return render_template('samples.html', samples=samples)


@app.route('/sample/<int:id>')
def sample(id):
    """Sample page."""
    sample = Sample.query.get(id)
    return render_template('sample.html', sample=sample)
