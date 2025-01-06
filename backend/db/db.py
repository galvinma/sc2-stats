import os
from contextlib import contextmanager

from dotenv import load_dotenv
from more_itertools import only
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

load_dotenv()

engine = create_engine(os.environ.get("PG_URI"))


@contextmanager
def session_scope():
    session = Session(bind=engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def query(session, params, joins=None, filters=None, distinct=None, order_by=None):
    stmt = session.query(*params)

    if joins:
        for tbl, condition in joins:
            stmt = stmt.join(tbl, condition)

    if filters:
        for filter in filters:
            stmt = stmt.filter(filter)

    if distinct:
        stmt = stmt.distinct(*distinct)

    if order_by is not None:
        stmt = stmt.order_by(order_by)

    return stmt.all()


def upsert(session, model, filter, values):
    instance = only(session.query(model).filter_by(**filter).all())
    if instance:
        for key, value in values.items():
            setattr(instance, key, value)
    else:
        instance = model(**values)

    session.add(instance)
    session.commit()
    return instance


def insert(session, model, values):
    instance = model(**values)
    session.add(instance)
    session.commit()
    return instance


def get_or_create(session, model, filter, values):
    """
    https://stackoverflow.com/questions/2546207/does-sqlalchemy-have-an-equivalent-of-djangos-get-or-create
    """
    instance = session.query(model).filter_by(**filter).first()
    if instance:
        return instance

    instance = model(**values)
    session.add(instance)
    session.commit()
    return instance
