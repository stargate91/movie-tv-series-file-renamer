import logging
from utils.logger import setup_logger
from core.db.database import LibraryDB
from core.engine.scanner import SmartScanner
from core.engine.collector import Collector
from core.engine.resolver import Resolver
from core.engine.formatter import Formatter
from core.engine.collision_resolver import CollisionResolver
from core.engine.executor import Executor
from core.config.manager import ConfigManager

logger = logging.getLogger(__name__)

class RenamerEngineV3:
    """
    Unified Orchestrator for the v3.0 Renaming Pipeline.
    Connects all modules: Scanner -> Collector -> Resolver -> Formatter -> Executor.
    """
    
    def __init__(self):
        setup_logger() # Initialize global logging
        self.config = ConfigManager()
        self.db = LibraryDB()
        
        # Initialize modules
        self.scanner = SmartScanner(self.config.settings, self.db)
        self.collector = Collector(self.db)
        self.resolver = Resolver(self.db, self.config.settings)
        self.formatter = Formatter(self.db)
        self.collision_resolver = CollisionResolver(self.config.settings)
        self.executor = Executor(self.db, self.formatter, self.collision_resolver, self.config.settings)

    def full_scan_and_resolve(self, path, cb=None):
        """
        Runs the complete discovery and identification pipeline.
        1. Scan local files
        2. Collect technical data & internal tags
        3. Resolve against APIs (TMDB/OMDb)
        """
        if cb: cb("Scanning directory...", 0, 100)
        self.scanner.scan_directory(path)
        
        if cb: cb("Collecting metadata (FFmpeg/GuessIt)...", 20, 100)
        self.collector.collect_all(cb=lambda msg, cur, tot: cb(msg, 20 + (cur/tot * 30), 100) if cb else None)
        
        if cb: cb("Identifying media with APIs...", 50, 100)
        self.resolver.resolve_all(cb=lambda msg, cur, tot: cb(msg, 50 + (cur/tot * 50), 100) if cb else None)
        
        if cb: cb("Pipeline complete.", 100, 100)
        return True

    def get_rename_plan(self, file_ids=None):
        """
        Generates a preview plan for the given files (or all identified files).
        """
        if not file_ids:
            # Fetch all identified video files
            videos = self.db.get_files_by_category('video')
            file_ids = [v['id'] for v in videos if v.get('status') != 'deleted']
            
            # Also include their extras
            all_ids = []
            for fid in file_ids:
                all_ids.append(fid)
                extras = self.db._get_connection().execute("SELECT id FROM media_files WHERE parent_file_id = ?", (fid,)).fetchall()
                all_ids.extend([e['id'] for e in extras])
            file_ids = all_ids

        return self.executor.create_plan(file_ids)

    def apply_plan(self, plan):
        """
        Physically renames/moves files based on the plan.
        """
        return self.executor.execute_plan(plan)

    def undo_operation(self, history_id):
        """
        Reverses a specific rename operation.
        """
        return self.executor.undo_rename(history_id)

    def get_history(self, limit=100):
        """
        Returns recent rename history.
        """
        with self.db._get_connection() as conn:
            return conn.execute("""
                SELECT rh.*, mf.file_name 
                FROM rename_history rh
                JOIN media_files mf ON rh.file_id = mf.id
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
