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

    def scan_directory(self, root_path, progress_callback=None):
        """Recursively scans a directory and populates the database."""
        # 1. First Pass: Collect all files and identify main videos
        all_files = []
        for root, dirs, files in os.walk(root_path):
            for f in files:
                abs_path = os.path.abspath(os.path.join(root, f))
                all_files.append(abs_path)

        # 2. Categorize and Add to DB
        video_ids = {} # path -> db_id
        asset_ids = [] # list of (path, category, size, db_id)
        total_files = len(all_files)

        for i, path in enumerate(all_files):
            if progress_callback:
                progress_callback(f"Scanning: {os.path.basename(path)}", i + 1, total_files)
            
            ext = os.path.splitext(path)[1].lower()
            ext = os.path.splitext(path)[1].lower()
            size_mb = os.path.getsize(path) / (1024 * 1024)
            
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
                existing = self.db.get_file_by_path(path)
                if existing:
                    # File already in DB, skip adding but still record it for linking
                    db_id = existing['id']
                else:
                    db_id = self.db.add_file(path, category, os.path.getsize(path), sub_category=sub_category)
                
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
