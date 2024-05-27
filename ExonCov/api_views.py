"""
ExonCov REST API routes.
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


@app.route('/api/samples/id/<sample_id>')
@token_required
def sample_by_id_api(sample_id):
    """
    Method to return sample details for the REST API

    Args:
        sample_id (str): Sample name to look up the details for

    Returns:
        Sample details as a JSON object

    """
    if get_sample_by_id(sample_id):
        result = model_to_dict(get_sample_by_id(sample_id))
    else:
        result = generate_not_found_dict()
    return jsonify(result)


@app.route('/api/samples/id/<sample_id>/panel/<panel_id>/qc')
@token_required
def sample_coverage_by_id_api(sample_id, panel_id):
    """
    Method to return sample QC details for the REST API

    Args:
        sample_id (int): Sample database ID to lookup
        panel_id (str): Panel to lookup

    Returns:
        QC details for the requested sample and panel as a JSON object
    """
    qc = get_qc_for_sample_and_panel(sample_id, panel_id, True)
    if qc:
        result = {"qc": qc}
        result["qc"]["summary"] = get_summary_by_sample_id_and_panel_id(sample_id, panel_id, True)
    else:
        result = generate_not_found_dict()

    return jsonify(result)


@app.route('/api/samples')
@token_required
def get_samples_api():
    """
    Method to look up all samples in the database

    Returns:
        List of found samples as JSON object
    """
    sample_name = request.args.get('sample_name') or ''
    run_id = request.args.get('run_id') or ''

    samples = get_sample_by_like_sample_name_or_run_id(sample_name, run_id)

    samples_list = []
    for sample in samples:
        sample = model_to_dict(sample)
        sample.pop("import_command")
        samples_list.append(sample)
    return jsonify(samples_list)


@app.route('/api/samples/<sample_name>/run/<run_id>')
@token_required
def get_summary_by_sample_name_and_run_id_api(sample_name, run_id):
    """
    Look up a sample by its name and run_id

    Args:
        sample_name (str): name of the sample
        run_id (str): run_id to look for

    Returns:

    """
    samples = get_samples_by_like_sample_name_or_like_run_id(sample_name, run_id)
    samples_list = []
    for sample in samples:
        samples_list.append(model_to_dict(sample))
    return jsonify(samples_list)


@app.route('/api/samples/name/<sample_name>')
@token_required
def get_sample_by_sample_name_api(sample_name):
    """
    Look up a sample by its name

    Args:
        sample_name (str): Sample name

    Returns:
        The sample as a JSON object if it is found in the database
    """
    if get_sample_by_id(sample_name):
        result = get_sample_by_sample_name(sample_name)
    else:
        result = generate_not_found_dict()
    return jsonify(model_to_dict(result))


@app.route('/api/samples/run/<run_id>')
@token_required
def get_summary_by_run_id_api(run_id):
    """
        Look up samples by its run ID

        Args:
            run_id (str): run id

        Returns:
            A list of sample as a JSON object if there are any found in the database
        """
    samples = get_sample_by_like_run_id(run_id)
    samples_list = []
    for sample in samples:
        samples_list.append(model_to_dict(sample))
    return jsonify(samples_list)
