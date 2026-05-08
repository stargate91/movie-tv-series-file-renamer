import os
import logging
from PySide6.QtCore import QThread, Signal
from core.i18n import T

logger = logging.getLogger(__name__)

class DataLoader(QThread):
    """Background thread for loading data and collecting poster paths."""
    finished = Signal(list, list)  # videos, poster_paths
    progress = Signal(int, str)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def run(self):
        try:
            # Use optimized batch fetch
            videos = self.engine.db.files.get_files_with_metadata('video', 'extra', 'subtitle', 'audio', 'image', 'metadata', 'unknown')
            
            status_priority = {'multiple': 0, 'no_match': 1, 'uncertain': 2, 'matched': 3, 'pending': 4}
            videos.sort(key=lambda v: status_priority.get(v.get('match_status', 'pending'), 99))

            # Create a lookup map for prefetched data to help the formatter
            prefetched_map = {v['id']: v for v in videos}

            # Collect poster paths and generate preview names here (off main thread)
            poster_paths = []
            rename_plan = []
            
            for vid in videos:
                try:
                    # Pre-generate the new name for the preview column using prefetched data
                    new_name = self.engine.formatter.generate_name(vid['id'], self.engine.config.settings, prefetched_data=prefetched_map)
                    if new_name:
                        ext = vid.get('extension', '')
                        proposed_full = f"{new_name}{ext}"
                        vid['_new_name'] = proposed_full
                        
                        # Add to a plan for collision detection
                        rename_plan.append({
                            'file_id': vid['id'],
                            'original_path': vid['current_path'],
                            'proposed_path': proposed_full,
                            'category': vid.get('category', 'video')
                        })
                        
                    # Poster paths from our joined query
                    if vid.get('media_poster'):
                        poster_paths.append(vid['media_poster'])
                    if vid.get('episode_poster'):
                        poster_paths.append(vid['episode_poster'])
                    if vid.get('season_poster'):
                        poster_paths.append(vid['season_poster'])
                except:
                    pass

            # --- Auto-Resolve Collisions for Preview ---
            if rename_plan:
                from core.engine.collision_resolver import CollisionResolver
                resolver = CollisionResolver(self.engine.config.settings)
                safe, collisions = resolver.detect_collisions(rename_plan)
                
                # Try to auto-resolve each collision group
                for group in collisions.values():
                    resolved = resolver.auto_resolve_group(group)
                    if resolved:
                        # Update the _new_name in our main videos list
                        for item in resolved:
                            vid = prefetched_map.get(item['file_id'])
                            if vid:
                                vid['_new_name'] = item['proposed_path']
                                # Mark as resolved so split_data knows it's no longer a conflict
                                vid['_is_resolved_collision'] = True

            self.finished.emit(videos, poster_paths)
        except Exception as e:
            logger.error(f"DataLoader Error: {e}")
            self.finished.emit([], [])

class PosterPrefetcher(QThread):
    """Prefetches poster images in the background."""
    def __init__(self, engine, poster_paths):
        super().__init__()
        self.engine = engine
        self.poster_paths = poster_paths

    def run(self):
        for path in self.poster_paths:
            if not path: continue
            try:
                # Use LibraryManager which has the download logic
                self.engine.resolver.library.pre_download_poster(path)
            except:
                pass

class RenameWorker(QThread):
    """Handles the physical renaming process in the background."""
    finished = Signal(dict)
    progress = Signal(int, str)

    def __init__(self, engine, plan):
        super().__init__()
        self.engine = engine
        self.plan = plan
        self._is_cancelled = False

    def stop(self):
        self._is_cancelled = True

    def run(self):
        try:
            def cb(curr, total, path):
                if self._is_cancelled: return False
                pct = int((curr / total) * 100)
                self.progress.emit(pct, T("discovery.messages.moving", filename=os.path.basename(path)))
                return True

            results = self.engine.executor.execute_plan(self.plan, progress_callback=cb)
            self.finished.emit(results)
        except Exception as e:
            self.finished.emit({'success': 0, 'failed': 1, 'skipped': 0, 'deleted': 0, 'errors': [str(e)]})

class UndoWorker(QThread):
    """Handles reversing a rename batch in the background."""
    finished = Signal(dict)
    progress = Signal(int, str)

    def __init__(self, engine, batch_id):
        super().__init__()
        self.engine = engine
        self.batch_id = batch_id
        self._is_cancelled = False

    def stop(self):
        self._is_cancelled = True

    def run(self):
        try:
            def cb(curr, total, path):
                if self._is_cancelled: return False
                pct = int((curr / total) * 100)
                self.progress.emit(pct, f"Restoring: {os.path.basename(path)}")
                return True

            success, failed, errors = self.engine.executor.undo_batch(self.batch_id, progress_callback=cb)
            self.finished.emit({'success': success, 'failed': failed, 'errors': errors})
        except Exception as e:
            self.finished.emit({'success': 0, 'failed': 1, 'errors': [str(e)]})

class PlanWorker(QThread):
    """Handles the heavy lifting of generating the rename plan."""
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int, str)

    def __init__(self, engine, videos):
        super().__init__()
        self.engine = engine
        self.videos = videos

    def run(self):
        try:
            file_ids = [v['id'] for v in self.videos] if self.videos else None
            plan = self.engine.get_rename_plan(file_ids=file_ids)
            self.finished.emit(plan)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit([])

class DropProcessor(QThread):
    """Processes dropped files/folders, checks duplicates, and enriches data."""
    finished = Signal()
    progress = Signal(int, str)

    def __init__(self, engine, paths):
        super().__init__()
        self.engine = engine
        self.paths = paths

    def run(self):
        try:
            # 1. Expand paths (if folders were dropped)
            all_files = []
            for path in self.paths:
                if os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for f in files:
                            all_files.append(os.path.join(root, f))
                else:
                    all_files.append(path)
            
            if not all_files:
                self.finished.emit()
                return

            # Sort by size descending: ensures main videos are processed BEFORE extras/subtitles,
            # so that parent linking finds the video already in the database.
            all_files.sort(key=lambda x: os.path.getsize(x) if os.path.exists(x) else 0, reverse=True)

            total = len(all_files)
            allowed_exts = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.m4v', '.mpg', '.mpeg', 
                            '.srt', '.sub', '.ass', '.vtt', 
                            '.mp3', '.flac', '.m4a', '.wav', '.ogg'}
            
            for i, file_path in enumerate(all_files):
                abs_path = os.path.abspath(file_path)
                ext = os.path.splitext(abs_path)[1].lower()
                
                if ext not in allowed_exts:
                    continue
                
                # Update progress
                self.progress.emit(int((i / total) * 100), T("discovery.messages.ingesting", filename=os.path.basename(abs_path)))
                
                # 2. Duplicate check
                existing = self.engine.db.files.get_file_by_path(abs_path)
                if existing: continue
                
                # 3. Basic Scan & DB Insert (with is_manual=1)
                file_id = self.engine.scanner.scan_single_file(abs_path)
                if file_id:
                    self.engine.db.update_file(file_id, is_manual=1)
                    
                    # 4. Immediate Enrich
                    self.engine.collector.collect_single_file(file_id)
                    self.engine.resolver.resolve_file(file_id)
            
            self.progress.emit(100, "Ingestion complete.")
            self.finished.emit()
            
        except Exception as e:
            logger.error(f"DropProcessor Error: {e}")
            self.finished.emit()

class SyncWorker(QThread):
    """Handles the full discovery pipeline: Scan -> Collect -> Resolve."""
    progress = Signal(int, str)
    finished = Signal()

    def __init__(self, engine, path):
        super().__init__()
        self.engine = engine
        self.path = path
        self._is_cancelled = False

    def stop(self):
        self._is_cancelled = True

    def run(self):
        try:
            def cb(msg, cur, tot):
                if self._is_cancelled: return False
                self.progress.emit(int(cur), msg)
                return True
            
            self.engine.full_scan_and_resolve(self.path, cb=cb)
            self.finished.emit()
        except Exception as e:
            logger.error(f"SyncWorker Error: {e}")
            self.finished.emit()

class LanguageFetchWorker(QThread):
    """Fetches missing metadata languages for specific items in the background."""
    progress = Signal(int, str)
    finished = Signal()

    def __init__(self, engine, item_ids=None):
        super().__init__()
        self.engine = engine
        self.item_ids = item_ids
        self._is_cancelled = False

    def stop(self):
        self._is_cancelled = True

    def run(self):
        try:
            target_lang = self.engine.config.settings.metadata_language
            
            if self.item_ids:
                media_items_to_check = []
                for fid in self.item_ids:
                    links = self.engine.db.media.get_links_for_file(fid)
                    for link in links:
                        media_items_to_check.append(link['media_item_id'])
                # Deduplicate
                media_items_to_check = list(set(media_items_to_check))
                
                # Fetch full media item details
                media_items = []
                for m_id in media_items_to_check:
                    m = self.engine.db.media.get_media_item_by_id(m_id)
                    if m: media_items.append(m)
            else:
                media_items = self.engine.db.media.get_all_media_items()
            
            # Filter those that don't have the current target language
            to_fetch = []
            for item in media_items:
                fetched_langs = item.get('fetched_languages', '')
                fetched_list = [l.strip() for l in fetched_langs.split(',') if l.strip()]
                needs_fetch = target_lang not in fetched_list
                
                # Check episodes if it's a TV show and series claims to be fetched
                if not needs_fetch and item.get('media_type') == 'tv':
                    # Instead of checking all links, check some episodes of this series
                    eps = self.engine.db._get_connection().execute(
                        "SELECT fetched_languages FROM tv_episodes WHERE media_item_id = ? LIMIT 20",
                        (item['id'],)
                    ).fetchall()
                    for ep in eps:
                        ep_f = [l.strip() for l in (ep['fetched_languages'] or "").split(',') if l.strip()]
                        if target_lang not in ep_f:
                            needs_fetch = True
                            break

                if needs_fetch:
                    to_fetch.append(item)
            total = len(to_fetch)
            if total == 0:
                self.progress.emit(100, T("discovery.messages.up_to_date") if T("discovery.messages.up_to_date") != "discovery.messages.up_to_date" else "Language metadata is already up to date.")
                self.finished.emit()
                return
                
            for i, item in enumerate(to_fetch):
                if self._is_cancelled: break
                
                # Update progress
                title = item.get('title', 'Unknown')
                self.progress.emit(int((i / total) * 100), f"Fetching {target_lang} for: {title}")
                
                # Trigger fetch via LibraryManager
                tmdb_id = item.get('tmdb_id')
                media_type = item.get('media_type')
                if tmdb_id:
                    self.engine.resolver.library.store_result({'tmdb_id': tmdb_id, 'media_type': media_type}, language_override=target_lang)
                    
            self.progress.emit(100, T("discovery.messages.fetch_complete") if T("discovery.messages.fetch_complete") != "discovery.messages.fetch_complete" else "Language fetching complete.")
            self.finished.emit()
        except Exception as e:
            logger.error(f"LanguageFetchWorker Error: {e}")
            self.finished.emit()

class SingleEnrichWorker(QThread):
    """Enriches a single media item with a specific language in the background."""
    finished = Signal()

    def __init__(self, engine, tmdb_id, media_type, language):
        super().__init__()
        self.engine = engine
        self.tmdb_id = tmdb_id
        self.media_type = media_type
        self.language = language

    def run(self):
        try:
            self.engine.resolver.library.store_result({
                'tmdb_id': self.tmdb_id, 
                'media_type': self.media_type
            }, language_override=self.language)
            self.finished.emit()
        except Exception as e:
            logger.error(f"SingleEnrichWorker Error: {e}")
            self.finished.emit()
