"""
ExonCov API routes.
Currently only used to implement api calls for select2 forms (ajax).
"""
from flask import request, jsonify
from flask_security import login_required
from jose import jwt

from . import app
from .models import Sample


@app.route('/api/sample')
@login_required
def api_samples():
    search_term = request.args.get('term')

    samples = (
        Sample.query
        .filter(Sample.name.like('%{0}%'.format(search_term)))
        .order_by(Sample.import_date.desc())
        .order_by(Sample.name.asc())
        .all()
    )

    result = {'results': [{'id': sample.id, 'text': str(sample)} for sample in samples]}
    return jsonify(result)
