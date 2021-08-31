"""Utility functions."""
import json

from flask import request, url_for
from flask_login import current_user
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError


def get_one_or_create(session, model, create_method='', create_method_kwargs=None, **kwargs):
    """Get object from database or create if not exist.

    Source: http://skien.cc/blog/2014/02/06/sqlalchemy-and-race-conditions-follow-up/
    """
    try:
        return session.query(model).filter_by(**kwargs).one(), True
    except NoResultFound:
        kwargs.update(create_method_kwargs or {})
        created = getattr(model, create_method, model)(**kwargs)
        try:
            session.add(created)
            session.flush()
        except IntegrityError:
            session.rollback()
            return session.query(model).filter_by(**kwargs).one(), True
        else:
            session.commit()
            return created, False


class WSGIMiddleware(object):
    """WSGI Middleware."""

    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = self.prefix
        return self.app(environ, start_response)


def url_for_other_page(page):
    args = request.args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


def weighted_average(values, weights):
    return sum(x * y for x, y in zip(values, weights)) / sum(weights)


def event_logger(connection, log_model, model_name, action, event_data):
    # Cleanup and transform item to str
    for item in event_data.keys():
        if item in ['_sa_instance_state', 'user']:
            event_data.pop(item, None)
        else:
            event_data[item] = str(event_data[item])

    connection.execute(
        log_model.__table__.insert(),
        {
            'user_id': current_user.id,
            'table': model_name,
            'action': action,
            'data': json.dumps(event_data)
        }
    )

def retrieve_coverage(sample_set_id):
    sample_set = SampleSet.query.options(
        joinedload('samples')).get_or_404(sample_set_id)
    measurement_type_form = MeasurementTypeForm()

    sample_ids = [sample.id for sample in sample_set.samples]
    measurement_type = [measurement_type_form.data['measurement_type'], dict(
        measurement_type_form.measurement_type.choices).get(measurement_type_form.data['measurement_type'])]
    panels_measurements = {}

    query = db.session.query(PanelVersion, TranscriptMeasurement).filter_by(active=True).filter_by(validated=True).join(Transcript, PanelVersion.transcripts).join(
        TranscriptMeasurement).filter(TranscriptMeasurement.sample_id.in_(sample_ids)).order_by(PanelVersion.panel_name).all()

    for panel, transcript_measurement in query:
        sample = transcript_measurement.sample
        if panel not in panels_measurements:
            panels_measurements[panel] = {
                'panel': panel,
                'samples': {},
            }

        if sample not in panels_measurements[panel]['samples']:
            panels_measurements[panel]['samples'][sample] = {
                'len': transcript_measurement.len,
                'measurement': transcript_measurement[measurement_type[0]]
            }
        else:
            panels_measurements[panel]['samples'][sample]['measurement'] = weighted_average(
                [panels_measurements[panel]['samples'][sample]['measurement'],
                    transcript_measurement[measurement_type[0]]],
                [panels_measurements[panel]['samples'][sample]
                    ['len'], transcript_measurement.len]
            )
            panels_measurements[panel]['samples'][sample]['len'] += transcript_measurement.len

    for panel in panels_measurements:
        values = [panels_measurements[panel]['samples'][sample]
                  ['measurement'] for sample in sample_set.samples]
        panels_measurements[panel]['min'] = min(values)
        panels_measurements[panel]['max'] = max(values)
        panels_measurements[panel]['mean'] = float(sum(values)) / len(values)
    return(sample_set, measurement_type_form, measurement_type, panels_measurements)
