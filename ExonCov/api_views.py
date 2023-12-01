"""
ExonCov API routes.
Currently only used to implement api calls for select2 forms (ajax).
"""
from flask import request, jsonify

from .auth_middleware import token_required
from .services import *
from .utils import model_to_dict


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


@app.route('/api/protected-by-token')
@token_required
def protected_api():
    return "success"


@app.route('/api/sample/<sample_id>')
@token_required
def sample_by_id_api(sample_id):
    print("lookup {}".format(sample_id))
    result = model_to_dict(get_sample_by_id(sample_id))
    # To omit items from the object:
    # result.pop("key")
    return jsonify(result)
