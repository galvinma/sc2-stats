import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
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


def insert_stmt(model, values, returning=None):
    stmt = insert(model).values(values)

    if returning:
        stmt = stmt.returning(returning)

    return stmt


def bulk_insert(session, stmt, constraint):
    session.execute(
        stmt.on_conflict_do_nothing(
            constraint=constraint,
        )
    )


def bulk_upsert(session, stmt, constraint, set_):
    session.execute(
        stmt.on_conflict_do_update(
            constraint=constraint,
            set_=set_,
        )
    )


def get_or_create(session, model, filter, values):
    instance = session.query(model).filter_by(**filter).first()
    if instance:
        return instance

    instance = model(**values)
    session.add(instance)
    session.commit()
    return instance


def orm_classes_as_dict(iterable):
    return [target.as_dict() for target in iterable]
