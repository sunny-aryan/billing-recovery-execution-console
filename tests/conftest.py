import pytest

from src import database
from src.seed import seed_database


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    """
    Create an isolated SQLite database for each test.

    This prevents tests from reading or modifying the local app database.
    """
    test_db_path = tmp_path / "test_billing_recovery.db"

    monkeypatch.setattr(database, "DB_PATH", test_db_path)

    database.initialize_database()
    seed_database()

    return test_db_path