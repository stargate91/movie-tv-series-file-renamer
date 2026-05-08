"""
v3.1 Collector: Orchestrates local metadata extraction.
Decomposed into NFOParser, TechnicalProber, and FilenameParser.
"""

import logging
import concurrent.futures
import threading
from core.engine.collector.nfo_parser import NFOParser
from core.engine.collector.technical_prober import TechnicalProber
from core.engine.collector.filename_parser import FilenameParser

logger = logging.getLogger(__name__)

class Collector:
    """
    Coordinates local metadata extraction.
    No API calls. Only reads files and writes to the database.
    """

    def __init__(self, db):
        self.db = db
        self.nfo = NFOParser()
        self.prober = TechnicalProber()
        self.guesser = FilenameParser()

    def collect_all(self, progress_callback=None):
        """Runs all three collection phases sequentially with unified progress reporting."""
        # Calculate total workload
        nfo_targets = [f for f in self.db.files.get_files_by_category('metadata') if f['extension'] == '.nfo' and f['parent_file_id']]
        media_files = self.db.files.get_files_by_category('video', 'audio')
        ffmpeg_targets = [v for v in media_files if not v.get('video_codec')]
        guessit_targets = [v for v in self.db.files.get_files_by_category('video', 'audio', 'subtitle') if not v.get('fn_title')]
        
        total_tasks = len(nfo_targets) + len(ffmpeg_targets) + len(guessit_targets)
        if total_tasks == 0:
            if progress_callback: progress_callback("Local data synced.", 1, 1)
            return

        current_task_offset = 0

        def unified_cb(msg, cur, tot):
            if progress_callback:
                # Use the phase-specific progress added to the global offset
                return progress_callback(msg, current_task_offset + cur, total_tasks)
            return True

        # Phase 1: NFO
        self._phase_nfo(unified_cb, nfo_targets)
        current_task_offset += len(nfo_targets)

        # Phase 2: FFmpeg
        self._phase_ffmpeg(unified_cb, ffmpeg_targets)
        current_task_offset += len(ffmpeg_targets)

        # Phase 3: GuessIt
        self._phase_guessit(unified_cb, guessit_targets)

    def collect_single_file(self, file_id):
        """Enriches a single file with technical and filename metadata."""
        vid = self.db.files.get_file_by_id(file_id)
        if not vid: return
            
        # 1. Technical (FFmpeg)
        if vid.get('category') in ('video', 'audio'):
            data = self.prober.probe(vid['current_path'])
            if data: self.db.files.update_file(file_id, **data)
        
        # 2. Filename (GuessIt)
        data = self.guesser.parse(vid['current_path'])
        if data: self.db.files.update_file(file_id, **data)

    def _phase_nfo(self, cb=None, to_process=None):
        """Phase 1: IMDB IDs from .nfo files."""
        if to_process is None:
            nfo_files = self.db.files.get_files_by_category('metadata')
            to_process = [f for f in nfo_files if f['extension'] == '.nfo' and f['parent_file_id']]
        
        total = len(to_process)
        for i, nfo in enumerate(to_process):
            if cb: 
                if cb(f"NFO: {nfo['file_name']}", i, total) is False: return
            
            imdb_id = self.nfo.parse_file(nfo['current_path'])
            if imdb_id:
                # Check if parent already has it to avoid redundant DB writes
                parent = self.db.files.get_file_by_id(nfo['parent_file_id'])
                if parent and not parent.get('nfo_imdb_id'):
                    self.db.files.update_file(nfo['parent_file_id'], nfo_imdb_id=imdb_id)

    def _phase_ffmpeg(self, cb=None, media_files=None):
        """Phase 2: Technical data using ffprobe (Concurrent)."""
        if media_files is None:
            all_media = self.db.files.get_files_by_category('video', 'audio')
            media_files = [v for v in all_media if not v.get('video_codec')]
        
        total = len(media_files)
        if total == 0:
            return

        def _worker(vid):
            data = self.prober.probe(vid['current_path'])
            if data:
                data['id'] = vid['id']
                return data
            return None

        updates = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_worker, v): v for v in media_files}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                res = future.result()
                if res: updates.append(res)
                if cb: 
                    if cb(f"FFmpeg: {futures[future]['file_name']}", i, total) is False:
                        executor.shutdown(wait=False, cancel_futures=True)
                        return
        
        if updates: self.db.files.bulk_update_files(updates)

    def _phase_guessit(self, cb=None, media_files=None):
        """Phase 3: Filename analysis using GuessIt (Concurrent)."""
        if media_files is None:
            all_media = self.db.files.get_files_by_category('video', 'audio', 'subtitle')
            media_files = [v for v in all_media if not v.get('fn_title')]
        
        total = len(media_files)
        if total == 0:
            return

        folder_cache = {}
        lock = threading.Lock()

        def _worker(vid):
            data = self.guesser.parse(vid['current_path'], folder_cache, lock)
            if data:
                data['id'] = vid['id']
                return data
            return None

        updates = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_worker, v): v for v in media_files}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                res = future.result()
                if res: updates.append(res)
                if cb: 
                    if cb(f"GuessIt: {futures[future]['file_name']}", i, total) is False:
                        executor.shutdown(wait=False, cancel_futures=True)
                        return
        
        if updates: self.db.files.bulk_update_files(updates)
