"""Store validated indicative ranges locally for 24 hours."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


ESTIMATE_TTL_SECONDS = 24 * 60 * 60
SavedRange = tuple[int, int, int]


class FareCache:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=1)
        try:
            with db:
                db.execute('CREATE TABLE IF NOT EXISTS fares (key TEXT PRIMARY KEY, low INTEGER NOT NULL, '
                           'high INTEGER NOT NULL, estimated_at INTEGER NOT NULL)')
                yield db
        finally:
            db.close()

    def lookup(self, key: str, now: int) -> SavedRange | None:
        with self.connect() as db:
            return db.execute('SELECT low, high, estimated_at FROM fares WHERE key = ? AND estimated_at > ?',
                              (key, now - ESTIMATE_TTL_SECONDS)).fetchone()

    def store(self, key: str, estimate: SavedRange) -> SavedRange:
        with self.connect() as db:
            db.execute('DELETE FROM fares WHERE estimated_at <= ?', (estimate[2] - ESTIMATE_TTL_SECONDS,))
            db.execute('INSERT INTO fares VALUES (?, ?, ?, ?) ON CONFLICT (key) DO NOTHING', (key, *estimate))
            return db.execute('SELECT low, high, estimated_at FROM fares WHERE key = ?', (key,)).fetchone()
