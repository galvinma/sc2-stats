import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(os.environ.get("PG_URI"))
Session = sessionmaker(engine)


def get_or_create(session, model, constraint, values):
    """
    https://stackoverflow.com/questions/2546207/does-sqlalchemy-have-an-equivalent-of-djangos-get-or-create
    """
    instance = session.query(model).filter_by(**constraint).first()
    if instance:
        return instance
    else:
        instance = model(**values)
        session.add(instance)
        session.commit()
        return instance
