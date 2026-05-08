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

    def wipe_discovery_data(self):
        """Clears all discovery data from DB and resets in-memory caches."""
        self.db.wipe_discovery_data()
        if hasattr(self.resolver, 'library'):
            self.resolver.library._enriched_ids.clear()
            self.resolver.library._omdb_auth_failed = False
            self.resolver.library._omdb_limit_reached = False

    def refresh_settings(self):
        """Resets engine state and propagates new settings to all modules."""
        s = self.config.settings
        
        # 1. Update Modules that store references to settings
        self.scanner.settings = s
        self.resolver.settings = s
        self.executor.settings = s
        self.collision_resolver.settings = s

        # 2. Re-initialize API clients inside modules to pick up new keys
        if hasattr(self.resolver, 'refresh_settings'):
            self.resolver.refresh_settings(s)
        
        # 3. Global API session reset
        from api.base_client import BaseClient
        BaseClient.reset_session()
        
        if hasattr(self.resolver, 'library'):
            self.resolver.library._omdb_auth_failed = False
            self.resolver.library._omdb_limit_reached = False

        logger.info("Engine settings refreshed and propagated.")

    @property
    def has_omdb_limit_reached(self):
        """Returns True if OMDb API limit was hit during this session."""
        if hasattr(self.resolver, 'library'):
            return self.resolver.library._omdb_limit_reached
        return False

    def full_scan_and_resolve(self, path, cb=None):
        """
        Runs the complete discovery and identification pipeline.
        1. Scan local files
        2. Collect technical data & internal tags
        3. Resolve against APIs (TMDB/OMDb)
        """
        if cb: 
            if cb("Scanning directory...", 0, 100) is False: return False
        if self.scanner.scan_directory(path, progress_callback=lambda msg, cur, tot: cb(msg, (cur/tot * 20), 100) if cb else None) is False: return False
        
        if cb: 
            if cb("Collecting metadata (FFmpeg/GuessIt)...", 20, 100) is False: return False
        if self.collector.collect_all(progress_callback=lambda msg, cur, tot: cb(msg, 20 + (cur/tot * 30), 100) if cb else None) is False: return False
        
        if cb: 
            if cb("Identifying media with APIs...", 50, 100) is False: return False
        if self.resolver.resolve_all(progress_callback=lambda msg, cur, tot: cb(msg, 50 + (cur/tot * 50), 100) if cb else None) is False: return False
        
        if cb: cb("Pipeline complete.", 100, 100)
        return True

    def get_rename_plan(self, file_ids=None):
        """
        Generates a preview plan for the given files (or all identified files).
        """
        if not file_ids:
            # Fetch only successfully MATCHED video files that are not deleted or already renamed
            videos = self.db.files.get_files_by_category('video')
            file_ids = [v['id'] for v in videos if (v.get('status') or '').upper() not in ('DELETED', 'RENAMED') 
                        and (v.get('match_status') or '').upper() == 'MATCHED']
            
            # Also include their extras (subtitles, bonus videos, etc.)
            all_ids = []
            for fid in file_ids:
                all_ids.append(fid)
                # Extras are included if their parent is matched, unless the extra itself is ignored
                extras = self.db.files.get_children(fid)
                all_ids.extend([e['id'] for e in extras if (e.get('match_status') or '').upper() != 'IGNORED'])
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
        return self.db.history.get_recent(limit)
