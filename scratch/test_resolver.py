import sys
import logging
from core.db.database import LibraryDB
from core.config.settings import Settings
from core.engine.resolver import Resolver

logging.basicConfig(level=logging.DEBUG)

def test_resolve():
    db = LibraryDB()
    settings = Settings()
    resolver = Resolver(db, settings)
    resolver.resolve_all()

if __name__ == "__main__":
    test_resolve()
