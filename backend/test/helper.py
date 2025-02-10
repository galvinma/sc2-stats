import unittest

import pytest
from dotenv import load_dotenv

from backend.db.db import ENGINE, session_scope
from backend.db.model import Base

load_dotenv()


def truncate_db():
    with session_scope(engine=ENGINE) as session:
        for table in Base.metadata.sorted_tables:
            session.execute(table.delete())
        session.commit()


class TestCaseBase(unittest.TestCase):
    def setUp(self):
        self.monkeypatch = pytest.MonkeyPatch()

        truncate_db()

    def tearDown(self):
        pass
        # self.postgresql.stop()
