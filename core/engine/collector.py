"""
v3.0 Collector: Extracts all available metadata from local sources.
No API calls. Only reads files and writes to the database.

Pipeline order:
  1. parse_nfo()     → IMDB ID from .nfo files
  2. probe_ffmpeg()  → technical data + internal title from video files
  3. parse_guessit() → title/year/season/episode from filename & foldername
"""

import os
import re
import json
import subprocess
import logging
from guessit import guessit

logger = logging.getLogger(__name__)


class Collector:
    """Runs all local metadata extraction and stores results in LibraryDB."""

    def __init__(self, db):
        self.db = db

    def collect_all(self, progress_callback=None):
        """Runs all three collection phases sequentially."""
        # Phase 1: NFO parsing
        self._phase_nfo(progress_callback)
        # Phase 2: FFmpeg probing
        self._phase_ffmpeg(progress_callback)
        # Phase 3: GuessIt parsing
        self._phase_guessit(progress_callback)

    def collect_single_file(self, file_id):
        """Enriches a single file with all local metadata (FFmpeg + GuessIt)."""
        vid = self.db.get_file_by_id(file_id)
        if not vid:
            return
            
        # 1. FFmpeg (if video/audio)
        if vid.get('category') in ('video', 'audio'):
            probe_data = self._probe_file(vid['current_path'])
            if probe_data:
                self.db.update_file(file_id, **probe_data)
        
        # 2. GuessIt
        guess_data = self._guess_file(vid)
        if guess_data:
            self.db.update_file(file_id, **guess_data)

    # ── Phase 1: NFO ────────────────────────────────────────────

    def _phase_nfo(self, cb=None):
        """Parses .nfo files to extract IMDB IDs (incremental)."""
        nfo_files = self.db.get_files_by_category('metadata')
        
        # We only care about NFOs where the parent doesn't have an IMDB ID yet
        to_process = []
        for nfo in nfo_files:
            if not nfo['extension'] == '.nfo': continue
            if nfo['parent_file_id']:
                parent = self.db.get_file_by_id(nfo['parent_file_id'])
                if parent and not parent.get('nfo_imdb_id'):
                    to_process.append(nfo)
        
        total = len(to_process)
        if total == 0:
            if cb: cb("NFO metadata already synced.", 1, 1)
            return

        for i, nfo in enumerate(to_process):
            if cb: cb(f"NFO: {nfo['file_name']}", i, total)
            
            if not nfo['extension'] == '.nfo':
                continue
            
            imdb_id = self._extract_imdb_from_nfo(nfo['current_path'])
            if imdb_id and nfo['parent_file_id']:
                # Write the IMDB ID to the parent video file
                self.db.update_file(nfo['parent_file_id'], nfo_imdb_id=imdb_id)
                logger.info(f"NFO → {imdb_id} for parent ID {nfo['parent_file_id']}")

    def _extract_imdb_from_nfo(self, nfo_path):
        """Extracts an IMDB ID from an .nfo file (supports Kodi XML and plain text URLs)."""
        try:
            # Try multiple encodings
            content = None
            for enc in ('utf-8', 'latin-1', 'cp1250'):
                try:
                    with open(nfo_path, 'r', encoding=enc) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if not content:
                return None

            # Pattern 1: Kodi XML <uniqueid type="imdb">tt1234567</uniqueid>
            match = re.search(r'<uniqueid[^>]*type=["\']imdb["\'][^>]*>(tt\d+)</uniqueid>', content, re.IGNORECASE)
            if match:
                return match.group(1)
            
            # Pattern 2: <imdbid>tt1234567</imdbid> or <id>tt1234567</id>
            match = re.search(r'<(?:imdbid|imdb|id)>(tt\d+)</(?:imdbid|imdb|id)>', content, re.IGNORECASE)
            if match:
                return match.group(1)

            # Pattern 3: Plain URL https://www.imdb.com/title/tt1234567/
            match = re.search(r'imdb\.com/title/(tt\d+)', content, re.IGNORECASE)
            if match:
                return match.group(1)
            
            # Pattern 4: Bare tt ID anywhere in the file
            match = re.search(r'\b(tt\d{7,})\b', content)
            if match:
                return match.group(1)

        except Exception as e:
            logger.warning(f"NFO parse error for {nfo_path}: {e}")
        
        return None

    # ── Phase 2: FFmpeg ─────────────────────────────────────────

    def _phase_ffmpeg(self, cb=None):
        """Probes video and audio files with ffprobe concurrently (incremental)."""
        import concurrent.futures
        
        # Incremental: Only probe files that don't have technical metadata yet
        all_media = self.db.get_files_by_category('video', 'audio')
        media_files = [v for v in all_media if not v.get('video_codec')]
        
        completed = 0
        total = len(media_files)
        
        if total == 0:
            if cb: cb("Technical data already collected.", 1, 1)
            return
        
        updates = []
        
        def _probe_worker(vid):
            probe_data = self._probe_file(vid['current_path'])
            if probe_data:
                probe_data['id'] = vid['id']
                return probe_data
            return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_probe_worker, vid): vid for vid in media_files}
            for future in concurrent.futures.as_completed(futures):
                vid = futures[future]
                try:
                    res = future.result()
                    if res:
                        updates.append(res)
                except Exception as e:
                    logger.error(f"FFmpeg probe error for {vid['file_name']}: {e}")
                
                completed += 1
                if cb: cb(f"FFmpeg: {vid['file_name']}", completed, total)
                
        if updates:
            self.db.bulk_update_files(updates)

    def _probe_file(self, file_path):
        """Runs ffprobe on a single file and returns a dict of extracted data."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-analyzeduration', '10000000',
                '-probesize', '10000000',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
            
            if result.returncode != 0:
                return None
            
            data = json.loads(result.stdout)
            return self._parse_ffprobe_json(data)
            
        except FileNotFoundError:
            logger.warning("ffprobe not found. Install FFmpeg and add to PATH.")
            return None
        except subprocess.TimeoutExpired:
            logger.warning(f"ffprobe timeout for {file_path}")
            return None
        except Exception as e:
            logger.warning(f"ffprobe error for {file_path}: {e}")
            return None

    def _parse_ffprobe_json(self, data):
        """Parses the raw ffprobe JSON into clean database columns."""
        result = {}
        fmt = data.get('format', {})
        streams = data.get('streams', [])
        
        # Duration
        dur = fmt.get('duration')
        if dur:
            try:
                result['duration'] = float(dur)
            except (ValueError, TypeError):
                pass
        
        # Internal title (MKV title tag)
        tags = fmt.get('tags', {})
        title = tags.get('title') or tags.get('TITLE')
        if title:
            result['internal_title'] = title
        
        # Video stream (first one)
        video_streams = [s for s in streams if s.get('codec_type') == 'video']
        if video_streams:
            vs = video_streams[0]
            w = vs.get('width', 0)
            h = vs.get('height', 0)
            if w and h:
                result['resolution'] = f"{w}x{h}"
            
            result['video_codec'] = vs.get('codec_name', '').upper()
            
            # Bitrate
            vbr = vs.get('bit_rate')
            if vbr:
                try:
                    result['video_bitrate'] = int(vbr) // 1000  # kbps
                except (ValueError, TypeError):
                    pass
            
            # Framerate
            fps = vs.get('r_frame_rate', '')
            if fps and '/' in fps:
                try:
                    num, den = fps.split('/')
                    fps_val = int(num) / int(den)
                    result['framerate'] = f"{fps_val:.3f}"
                except (ValueError, ZeroDivisionError):
                    result['framerate'] = fps
            
            # Bit depth
            bd = vs.get('bits_per_raw_sample')
            if bd:
                try:
                    result['bit_depth'] = int(bd)
                except (ValueError, TypeError):
                    pass
            
            # HDR detection
            result['hdr_type'] = self._detect_hdr(vs)
        
        # Audio streams
        audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
        audio_list = []
        for a_stream in audio_streams:
            a_info = {
                'codec': a_stream.get('codec_name', '').upper(),
                'channels': a_stream.get('channels'),
                'channel_layout': a_stream.get('channel_layout', ''),
                'language': (a_stream.get('tags', {}).get('language') or 
                           a_stream.get('tags', {}).get('LANGUAGE') or 'und'),
                'bitrate': None
            }
            abr = a_stream.get('bit_rate')
            if abr:
                try:
                    a_info['bitrate'] = int(abr) // 1000
                except (ValueError, TypeError):
                    pass
            audio_list.append(a_info)
        
        if audio_list:
            # Primary audio stream summary
            primary = audio_list[0]
            result['audio_codec'] = primary['codec']
            result['audio_channels'] = primary.get('channel_layout', str(primary.get('channels', '')))
            result['audio_bitrate'] = primary.get('bitrate')
            
            lang = primary.get('language')
            if lang and lang.lower() not in ('und', 'unknown'):
                result['language'] = lang.lower()
                
            result['audio_streams_json'] = json.dumps(audio_list, ensure_ascii=False)
        
        # Subtitle streams
        sub_streams = [s for s in streams if s.get('codec_type') == 'subtitle']
        sub_list = []
        for s_stream in sub_streams:
            s_info = {
                'codec': s_stream.get('codec_name', '').upper(),
                'language': (s_stream.get('tags', {}).get('language') or
                           s_stream.get('tags', {}).get('LANGUAGE') or 'und'),
                'forced': 'forced' in str(s_stream.get('disposition', {}))
            }
            sub_list.append(s_info)
        
        if sub_list:
            result['subtitle_streams_json'] = json.dumps(sub_list, ensure_ascii=False)
        
        # Full technical dump
        result['technical_json'] = json.dumps(data, ensure_ascii=False)
        
        return result

    def _detect_hdr(self, video_stream):
        """Detects HDR type from video stream metadata."""
        color_transfer = video_stream.get('color_transfer', '').lower()
        color_primaries = video_stream.get('color_primaries', '').lower()
        
        # Check side data for Dolby Vision
        side_data = video_stream.get('side_data_list', [])
        for sd in side_data:
            sd_type = sd.get('side_data_type', '').lower()
            if 'dovi' in sd_type or 'dolby vision' in sd_type:
                return 'Dolby Vision'
        
        if 'smpte2084' in color_transfer or 'st2084' in color_transfer:
            if 'bt2020' in color_primaries:
                return 'HDR10'
        
        if 'arib-std-b67' in color_transfer:
            return 'HLG'
        
        return 'SDR'

    # ── Phase 3: GuessIt ────────────────────────────────────────

    def _phase_guessit(self, cb=None):
        """Parses filename and foldername with GuessIt (incremental)."""
        import concurrent.futures
        import threading
        
        # Incremental: Only guess files that don't have filename metadata yet
        all_media = self.db.get_files_by_category('video', 'audio', 'subtitle')
        media_files = [v for v in all_media if not v.get('fn_title')]
        
        completed = 0
        total = len(media_files)
        
        if total == 0:
            if cb: cb("Filename analysis already done.", 1, 1)
            return
        
        folder_cache = {}
        folder_cache_lock = threading.Lock()
        
        def _guess_worker(vid):
            update = self._guess_file(vid, folder_cache, folder_cache_lock)
            if update:
                update['id'] = vid['id']
                return update
            return None
                
        updates = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_guess_worker, vid): vid for vid in media_files}
            for future in concurrent.futures.as_completed(futures):
                vid = futures[future]
                try:
                    res = future.result()
                    if res:
                        updates.append(res)
                except Exception as e:
                    logger.error(f"GuessIt error for {vid['file_name']}: {e}")
                
                completed += 1
                if cb: cb(f"GuessIt: {vid['file_name']}", completed, total)

        if updates:
            self.db.bulk_update_files(updates)

    def _guess_file(self, vid, folder_cache=None, lock=None):
        """Internal helper to guess metadata for a single file dict."""
        update = {}
        file_path = vid['current_path']
        
        # --- Filename GuessIt ---
        filename = os.path.splitext(os.path.basename(file_path))[0]
        fn_guess = guessit(filename)
        
        fn_title = fn_guess.get('title')
        if fn_title:
            update['fn_title'] = fn_title
        
        fn_year = fn_guess.get('year')
        if fn_year:
            update['fn_year'] = fn_year
        
        fn_season = fn_guess.get('season')
        if fn_season is not None:
            update['fn_season'] = fn_season
        
        fn_episode = fn_guess.get('episode')
        if fn_episode is not None:
            update['fn_episode'] = str(fn_episode)
        
        fn_type = fn_guess.get('type', 'movie')
        update['fn_media_type'] = fn_type
        update['sub_category'] = 'tv' if fn_type == 'episode' else fn_type
        
        # Extract language
        fn_lang = fn_guess.get('language')
        if fn_lang:
            if isinstance(fn_lang, list):
                update['language'] = str(fn_lang[0])
            else:
                update['language'] = str(fn_lang)
        
        # --- Foldername GuessIt ---
        parent_dir = os.path.basename(os.path.dirname(file_path))
        if parent_dir:
            fd_guess = None
            if folder_cache is not None and lock is not None:
                with lock:
                    if parent_dir in folder_cache:
                        fd_guess = folder_cache[parent_dir]
                    else:
                        fd_guess = guessit(parent_dir)
                        folder_cache[parent_dir] = fd_guess
            else:
                fd_guess = guessit(parent_dir)
            
            if fd_guess:
                fd_title = fd_guess.get('title')
                if fd_title:
                    update['fd_title'] = fd_title
                
                fd_year = fd_guess.get('year')
                if fd_year:
                    update['fd_year'] = fd_year
                
                fd_season = fd_guess.get('season')
                if fd_season is not None:
                    update['fd_season'] = fd_season
                
                fd_episode = fd_guess.get('episode')
                if fd_episode is not None:
                    update['fd_episode'] = str(fd_episode)
                
                fd_type = fd_guess.get('type', 'movie')
                update['fd_media_type'] = fd_type
                if 'sub_category' not in update:
                    update['sub_category'] = 'tv' if fd_type == 'episode' else fd_type
        
        return update
