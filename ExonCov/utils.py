"""Utility functions."""
import json
from builtins import str

from flask import request, url_for
from flask_login import current_user
from sqlalchemy.orm import class_mapper
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
    for item in list(event_data.keys()):
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


def get_summary_stats(values):
    return(min(values), max(values), float(sum(values)) / len(values))


def get_summary_stats_multi_sample(measurements, keys=None, samples=None):
    if not keys:
        keys = measurements.keys()
    elif isinstance(keys, str):
        keys = [keys]

    for key in keys:
        if samples and 'samples' in measurements[key]:
            # when measurements scope is panel
            values = [measurements[key]['samples'][sample]['measurement'] for sample in samples]
        elif samples:
            values = [measurements[key][sample]['measurement'] for sample in samples]
        else:
            # when measurements scope is transcript or exon
            values = measurements[key].values()
        measurements[key]['min'], measurements[key]['max'], measurements[key]['mean'] = get_summary_stats(values)
    return measurements


def model_to_dict(model_instance):
    return {column.name: getattr(model_instance, column.name) for column in class_mapper(model_instance.__class__).mapped_table.c}
