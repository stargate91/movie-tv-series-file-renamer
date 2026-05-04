import os
from core.db.database import LibraryDB

class SmartScanner:
    """
    v3.0 Scanner: Categorizes and links media assets (Video, Extra, Subtitle, Image).
    Writes directly to LibraryDB.
    """
    def __init__(self, settings, db=None):
        self.s = settings
        self.db = db or LibraryDB()
        
        # Prepare extension sets for fast lookup (Ensuring leading dots)
        def clean_exts(s):
            return {("." + e.strip().lower().lstrip(".")) for e in s.split(",") if e.strip()}

        self.video_exts = clean_exts(self.s.video_extensions)
        self.sub_exts = clean_exts(self.s.subtitle_extensions)
        self.audio_exts = clean_exts(self.s.audio_extensions)
        self.img_exts = clean_exts(self.s.image_extensions)
        self.meta_exts = clean_exts(self.s.metadata_extensions)

    def cleanup_missing_files(self):
        """Removes files from the database that no longer exist on disk."""
        existing = self.db.get_all_files()
        missing_ids = []
        for f in existing:
            if not os.path.exists(f['current_path']):
                missing_ids.append(f['id'])
                
        if missing_ids:
            with self.db._get_connection() as conn:
                # SQLite has a limit on the number of variables in an IN clause (usually 999),
                # so we delete in chunks.
                for i in range(0, len(missing_ids), 500):
                    chunk = missing_ids[i:i+500]
                    placeholders = ','.join(['?'] * len(chunk))
                    conn.execute(f"DELETE FROM media_files WHERE id IN ({placeholders})", chunk)
                    # Note: We do NOT delete from media_items, so TMDB cache is preserved!
                conn.commit()

    def scan_directory(self, root_path, progress_callback=None):
        """Recursively scans a directory and populates the database."""
        # 0. Clean up missing files first to prevent ghosts
        self.cleanup_missing_files()
        
        # 1. First Pass: Collect all files and identify main videos
        all_files = []
        for root, dirs, files in os.walk(root_path):
            for f in files:
                abs_path = os.path.abspath(os.path.join(root, f))
                all_files.append(abs_path)

        # Pre-load existing files to avoid N+1 queries (massively speeds up scanning)
        existing_files_list = self.db.get_all_files()
        existing_files = {f['current_path']: f for f in existing_files_list}

        # 2. Categorize and Add to DB
        video_ids = {} # path -> db_id
        asset_ids = [] # list of (path, category, db_id)
        total_files = len(all_files)

        for i, path in enumerate(all_files):
            if progress_callback:
                progress_callback(f"Scanning: {os.path.basename(path)}", i + 1, total_files)
            
            ext = os.path.splitext(path)[1].lower()
            size_bytes = os.path.getsize(path)
            size_mb = size_bytes / (1024 * 1024)
            
            category = 'unknown'
            if ext in self.video_exts:
                category = 'video' if size_mb >= self.s.vid_size else 'extra'
            elif ext in self.sub_exts:
                category = 'subtitle'
            elif ext in self.audio_exts:
                category = 'audio'
            elif ext in self.img_exts:
                category = 'image'
            elif ext in self.meta_exts:
                category = 'metadata'
            
            sub_category = None
            if category in ('video', 'extra'):
                name_lower = os.path.basename(path).lower()
                keywords = [k.strip().lower() for k in self.s.sample_keywords.split(',')]
                for k in keywords:
                    if k in name_lower:
                        # Map to sub_category: if keyword contains sample/minta -> sample, else trailer
                        if any(x in k for x in ('sample', 'minta')):
                            sub_category = 'sample'
                        else:
                            sub_category = 'trailer'
                        break
            
            if category != 'unknown':
                # Check if file already exists in DB
                if path in existing_files:
                    existing = existing_files[path]
                    db_id = existing['id']
                    # Only update if size or category changed
                    if existing['size_bytes'] != size_bytes or existing['category'] != category:
                        self.db.add_file(path, category, size_bytes, sub_category=sub_category)
                else:
                    db_id = self.db.add_file(path, category, size_bytes, sub_category=sub_category)
                
                if category == 'video':
                    video_ids[path] = db_id
                else:
                    asset_ids.append((path, category, db_id))

        # 3. Second Pass: Link Assets to Parents
        self._link_assets(asset_ids, video_ids)
        
        return len(video_ids)

    def _link_assets(self, asset_ids, video_ids):
        """Links subtitles, images, and extras to the most likely parent video."""
        video_paths = list(video_ids.keys())
        
        for path, category, db_id in asset_ids:
            parent_path = self._find_best_parent(path, video_paths)
            if parent_path:
                self.db.link_parent(db_id, video_ids[parent_path])

    def _find_best_parent(self, asset_path, video_paths):
        """Recursive parent lookup logic (Searching up to 3 levels)."""
        asset_dir = os.path.normpath(os.path.dirname(asset_path)).lower()
        asset_name = os.path.splitext(os.path.basename(asset_path))[0].lower()
        
        # Clean asset name from common tags for better matching
        target = asset_name.replace('sample', '').replace('trailer', '').strip(' -._')
        
        current_lookup = asset_dir
        for _ in range(3):
            # Find all videos in this folder (normalized comparison)
            folder_vids = [v for v in video_paths if os.path.normpath(os.path.dirname(v)).lower() == current_lookup]
            
            if folder_vids:
                # 1. Try exact/partial name match
                for v in folder_vids:
                    v_base = os.path.splitext(os.path.basename(v).lower())[0]
                    # If target title is in parent or parent title is in asset
                    if target and (target in v_base or v_base in target):
                        return v
                
                # 2. If only one video in folder, it's the parent
                if len(folder_vids) == 1:
                    return folder_vids[0]
                
                # 3. Sort folder videos by size (descending) and pick the largest as fallback
                try:
                    folder_vids.sort(key=lambda x: os.path.getsize(x), reverse=True)
                    return folder_vids[0]
                except:
                    if folder_vids: return folder_vids[0]

            # Move up
            new_dir = os.path.dirname(current_lookup)
            if new_dir == current_lookup or not new_dir: break
            current_lookup = new_dir
            
        return None

    def scan_single_file(self, path):
        """Scans a single file, adds to DB and attempts linking."""
        if not os.path.exists(path): return None
        
        ext = os.path.splitext(path)[1].lower()
        size_bytes = os.path.getsize(path)
        size_mb = size_bytes / (1024 * 1024)
        
        category = 'unknown'
        if ext in self.video_exts:
            category = 'video' if size_mb >= self.s.vid_size else 'extra'
        elif ext in self.sub_exts:
            category = 'subtitle'
        elif ext in self.audio_exts:
            category = 'audio'
        elif ext in self.img_exts:
            category = 'image'
        elif ext in self.meta_exts:
            category = 'metadata'
            
        if category == 'unknown': return None
        
        sub_category = None
        if category in ('video', 'extra'):
            name_lower = os.path.basename(path).lower()
            keywords = [k.strip().lower() for k in self.s.sample_keywords.split(',')]
            for k in keywords:
                if k in name_lower:
                    if any(x in k for x in ('sample', 'minta')):
                        sub_category = 'sample'
                    else:
                        sub_category = 'trailer'
                    break
        
        db_id = self.db.add_file(path, category, size_bytes, sub_category=sub_category)
        
        # Ensure we return the ID even if it was a duplicate/update
        if not db_id:
            existing = self.db.get_file_by_path(path)
            if existing: db_id = existing['id']
        
        if not db_id: return None

        # Attempt linking if it's an asset
        if category != 'video':
            # Get candidate videos (all videos in DB for now, _find_best_parent will filter them)
            nearby_vids = [f['current_path'] for f in self.db.get_all_files('video')]
            
            parent_path = self._find_best_parent(path, nearby_vids)
            if parent_path:
                parent_data = self.db.get_file_by_path(parent_path)
                if parent_data:
                    self.db.link_parent(db_id, parent_data['id'])
                    
        return db_id
