import os
from metadata.collector import get_all_video_files
from metadata.classifier import batch_classify

class ScanManager:
    """
    Handles file system scanning and initial media classification (Main vs Extra).
    """
    def __init__(self, settings, ui=None):
        self.s = settings
        self.ui = ui

    def collect_files(self, metadata_map):
        """
        Scans the configured folder and populates the initial metadata_map.
        """
        valid_exts = [ext.strip().lower() for ext in self.s.video_extensions.split(",") if ext.strip()]
        print(f"DEBUG: ScanManager starting collection in {self.s.folder_path}")
        
        if not self.s.folder_path or not os.path.exists(self.s.folder_path):
            print(f"ERROR: Invalid folder path: {self.s.folder_path}")
            return []
        
        # 1. Quick Scan
        video_files = []
        for f in get_all_video_files(self.s.folder_path, self.s.vid_size, self.s.recursive, valid_exts):
            video_files.append(f)
            if len(video_files) % 50 == 0:
                print(f"DEBUG: Found {len(video_files)} files so far...")
                if self.ui:
                    self.ui.update_progress(0, 0, f"Status: Found {len(video_files)} files...")

        total = len(video_files)
        if total == 0:
            if self.ui:
                self.ui.update_progress(100, 100, "Status: No video files found.")
            return []

        # 2. Linear Classification (Stupid Simple)
        print(f"DEBUG: Classifying {total} files...")
        chunk_size = max(1, total // 100)
        class_map = batch_classify(video_files, self.s.vid_size)
        print("DEBUG: Classification map built.")
        
        for i, path in enumerate(video_files):
            category, extra_type, parent_name = class_map.get(path, ('movie', None, None))
            
            if path not in metadata_map:
                metadata_map[path] = {
                    'file_path': path,
                    'file_type': category,
                    'extra_type': extra_type,
                    'extra_parent': parent_name,
                    'status': 'pending' if category != 'extra' else 'extra',
                    'is_manual': False,
                    'details': None,
                    'extras': {'title': os.path.basename(path)}
                }
            
            if self.ui and i % chunk_size == 0:
                percent = int((i / total) * 100)
                self.ui.update_progress(percent, 100, f"Status: Classifying {i}/{total}...")
        
        if self.ui:
            self.ui.update_progress(100, 100, f"Status: Scan Complete. Found {total} files.")
        
        return video_files
