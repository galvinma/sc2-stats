import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.utils.concurrency import thread_pool_max_workers

load_dotenv()


def get_engine():
    workers = thread_pool_max_workers()
    return create_engine(
        os.environ.get("PG_URI"),
        pool_size=workers,
        max_overflow=int(workers * 0.1),
        pool_timeout=30,
    )


@contextmanager
def session_scope():
    engine = get_engine()
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
