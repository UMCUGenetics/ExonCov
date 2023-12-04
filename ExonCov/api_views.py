"""
ExonCov API routes.
Currently only used to implement api calls for select2 forms (ajax).
"""
from flask import request, jsonify
from flask_login import login_required

from . import app
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


@app.route('/api/samples/id/<sample_id>')
@token_required
def sample_by_id_api(sample_id):
    print("lookup {}".format(sample_id))
    result = model_to_dict(get_sample_by_id(sample_id))
    # To omit items from the object:
    # result.pop("key")
    return jsonify(result)


@app.route('/api/samples/')
@token_required
def get_samples_api():
    sample_name = request.args.get('sample_name') or ''
    run_id = request.args.get('run_id') or ''

    print(sample_name)
    print(run_id)

    samples = get_sample_by_like_sample_name_or_run_id(sample_name, run_id)

    samples_list = []
    for sample in samples:
        sample = model_to_dict(sample)
        sample.pop("import_command")
        samples_list.append(sample)
    return jsonify(samples_list)


@app.route('/api/sample/<sample_name>/run/<run_id>/')
@token_required
def get_summary_by_sample_name_and_run_id_api(sample_name, run_id):
    samples = get_samples_by_like_sample_name_or_like_run_id(sample_name, run_id)
    samples_list = []
    for sample in samples:
        samples_list.append(model_to_dict(sample))
    return jsonify(samples_list)


@app.route('/api/sample/name/<name>/')
@token_required
def get_sample_by_like_sample_name_api(name):
    samples = get_sample_by_like_sample_name(name)
    samples_list = []
    for sample in samples:
        samples_list.append(model_to_dict(sample))
    return jsonify(samples_list)


@app.route('/api/sample/run/<run_id>/')
@token_required
def get_summary_by_run_id_api(run_id):
    samples = get_sample_by_like_run_id(run_id)
    samples_list = []
    for sample in samples:
        samples_list.append(model_to_dict(sample))
    return jsonify(samples_list)