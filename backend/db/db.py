import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.utils.concurrency import thread_pool_max_workers
from backend.utils.log import get_logger

load_dotenv()

logger = get_logger(__name__)


def get_engine():
    workers = thread_pool_max_workers()
    return create_engine(
        os.environ.get("PG_URI"),
        pool_size=workers,
        max_overflow=int(workers * 0.1),
        pool_timeout=30,
    )


ENGINE = get_engine()


@contextmanager
def session_scope(engine=None):
    if not engine:
        engine = ENGINE

    session = Session(bind=engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def query(
    params,
    joins=None,
    filters=None,
    filter_by=None,
    distinct=None,
    options=None,
    group_by=None,
    order_by=None,
    limit=None,
    count=None,
):
    with session_scope(engine=ENGINE) as session:
        stmt = session.query(*params)

        if joins:
            for tbl, condition in joins:
                stmt = stmt.join(tbl, condition)

        if filters:
            for filter in filters:
                stmt = stmt.filter(filter)

        if filter_by:
            stmt = stmt.filter_by(**filter_by)

        if distinct:
            stmt = stmt.distinct(*distinct)

        if options:
            stmt.options(options)

        if group_by is not None:
            stmt.group_by(*group_by)

        if order_by is not None:
            stmt = stmt.order_by(*order_by)

        if limit is not None:
            stmt = stmt.limit(limit)

        if count is not None:
            return stmt.count()

        res = stmt.all()
        session.expunge_all()
        return res


def insert_stmt(model, values):
    return insert(model).values(values)


def bulk_insert(stmt, constraint):
    with session_scope(engine=ENGINE) as session:
        session.execute(
            stmt.on_conflict_do_nothing(
                constraint=constraint,
            )
        )


def bulk_upsert(stmt, constraint, set_):
    with session_scope(engine=ENGINE) as session:
        session.execute(
            stmt.on_conflict_do_update(
                constraint=constraint,
                set_=set_,
            )
        )


def create(instance):
    with session_scope(engine=ENGINE) as session:
        session.add(instance)
        session.commit()
        return instance


def get_or_create(session, model, filter, values):
    instance = session.query(model).filter_by(**filter).first()
    if instance:
        return instance

    instance = model(**values)
    session.add(instance)
    session.commit()


def orm_classes_as_dict(iterable):
    return [target.as_dict() for target in iterable]
