"""Utility functions."""
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
        if item in ['_sa_instance_state', 'user', 'transcripts', 'panel']:
            event_data.pop(item, None)
        else:
            event_data[item] = str(event_data[item])

    connection.execute(
        log_model.__table__.insert(),
        {
            'user_id': current_user.id,
            'table': model_name,
            'action': action,
            'data': event_data
        }
    )
