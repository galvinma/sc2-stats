import os

from dotenv import load_dotenv
from more_itertools import only
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

engine = create_engine(os.environ.get("PG_URI"))
Session = sessionmaker(engine)


def query(params, filters=None):
    if filters is None:
        filters = {}

    with Session() as session:
        return session.query(*params).filter_by(**filters).all()


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
