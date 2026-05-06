"""
v3.1 SmartScanner: Orchestrates local media discovery.
Decomposed into PathCrawler and FileFilter.
"""

import os
import logging
from .crawler import PathCrawler
from .filter import FileFilter
from .linker import AssetLinker

logger = logging.getLogger(__name__)

class SmartScanner:
    """
    Main entry point for discovery.
    Identifies, categorizes, and links media files to parents in the database.
    Decomposed into specialized sub-components:
    - PathCrawler: Disk traversal and stats.
    - FileFilter: Categorization based on extension/size.
    - AssetLinker: Heuristic parent-child association.
    """
    def __init__(self, settings, db):
        self.s = settings
        self.db = db
        self.crawler = PathCrawler()
        self.filter = FileFilter(settings)
        self.linker = AssetLinker()

    def cleanup_missing_files(self):
        """Removes files from the database that no longer exist on disk."""
        existing = self.db.files.get_all_files()
        missing_ids = [f['id'] for f in existing if not self.crawler.check_exists(f['current_path'])]
                
        if missing_ids:
            # Chunking handled inside repository or here... 
            # I'll let repository handle the list, but keep chunking here if list is HUGE
            for i in range(0, len(missing_ids), 500):
                self.db.files.bulk_delete_files(missing_ids[i:i+500])
            logger.info(f"Cleaned up {len(missing_ids)} missing files from DB.")

    def scan_directory(self, root_path, progress_callback=None):
        """Recursively scans a directory and populates the database."""
        self.cleanup_missing_files()
        
        # Get ignore lists from settings if available
        exclude_dirs = set(self.s.ignore_folders.split(",")) if hasattr(self.s, 'ignore_folders') else None
        
        all_paths = self.crawler.walk(root_path, exclude_dirs=exclude_dirs)

        video_ids = {} # path -> db_id
        asset_ids = [] # list of (path, category, db_id)
        total = len(all_paths)

        for i, path in enumerate(all_paths):
            if progress_callback:
                res = progress_callback(f"Scanning: {os.path.basename(path)}", i + 1, total)
                if res is False:
                    logger.info("Scan aborted by user.")
                    break
            
            stats = self.crawler.get_stats(path)
            if not stats: continue

            category = self.filter.get_category(path)
            if category == 'unknown': continue
            
            sub_category = self.filter.get_sub_category(path, category)
            language = self.filter.get_language(path)
            part = self.filter.get_part(path)
            
            # Upsert logic via Repository
            db_id = self._upsert_file(path, category, stats['size_bytes'], sub_category, language, part)
            
            if category == 'video':
                video_ids[path] = db_id
            else:
                asset_ids.append((path, category, db_id))

        # Link Assets to Parents using AssetLinker
        self._link_assets(asset_ids, video_ids)
        return len(video_ids)

    def _upsert_file(self, path, category, size, sub_cat, language=None):
        """Adds or updates file in DB, returning its ID."""
        existing = self.db.get_file_by_path(path)
        if existing:
            if existing['size_bytes'] != size or existing['category'] != category or existing['sub_category'] != sub_cat or existing['language'] != language:
                self.db.update_file(existing['id'], category=category, size_bytes=size, sub_category=sub_cat, language=language)
            return existing['id']
        else:
            return self.db.files.add_file(path, category, size, sub_category=sub_cat, language=language)

    def _link_assets(self, asset_ids, video_ids):
        """Links subtitles, images, and extras to the most likely parent video."""
        video_paths = list(video_ids.keys())
        for path, category, db_id in asset_ids:
            parent_path = self.linker.find_best_parent(path, video_paths)
            if parent_path:
                self.db.files.link_parent(db_id, video_ids[parent_path])

    def scan_single_file(self, path):
        """Scans a single file, adds to DB and attempts linking."""
        stats = self.crawler.get_stats(path)
        if not stats: return None
        
        category = self.filter.get_category(path)
        if category == 'unknown': return None
        
        sub_category = self.filter.get_sub_category(path, category)
        language = self.filter.get_language(path)
        db_id = self.db.files.add_file(path, category, stats['size_bytes'], sub_category=sub_category, language=language)
        
        if not db_id: # Handle existing
            existing = self.db.files.get_file_by_path(path)
            if db_id := (existing['id'] if existing else None): pass
        
        if db_id and category != 'video':
            nearby_vids = [f['current_path'] for f in self.db.files.get_all_files('video')]
            parent_path = self.linker.find_best_parent(path, nearby_vids)
            if parent_path:
                parent_data = self.db.files.get_file_by_path(parent_path)
                if parent_data:
                    self.db.files.link_parent(db_id, parent_data['id'])
        return db_id
