class BaseRepository:
    """
    Base class for all repositories.
    Provides access to the database connection manager.
    """
    def __init__(self, db_manager):
        self.db = db_manager

    def _get_connection(self):
        return self.db._get_connection()
