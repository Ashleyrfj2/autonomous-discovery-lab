import sqlite3

import pytest

from autodiscover.orchestrator.migrations import MIGRATIONS
from autodiscover.orchestrator.store import StateError, Store


def test_upgrade_v1_and_refuse_future_schema(tmp_path):
    path = tmp_path / "lab.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript(MIGRATIONS[0])
        db.execute("PRAGMA user_version=1")
    store = Store(tmp_path)
    run = store.create_run("upgrade retained", {})
    assert Store(tmp_path).get_run(run)["topic"] == "upgrade retained"
    with store.connection(write=True) as db:
        db.execute("PRAGMA user_version=999")
    with pytest.raises(StateError, match="newer"):
        Store(tmp_path)
