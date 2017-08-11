"""Utility functions."""
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
            return created, False
        except IntegrityError:
            session.rollback()
            return session.query(model).filter_by(**kwargs).one(), True
