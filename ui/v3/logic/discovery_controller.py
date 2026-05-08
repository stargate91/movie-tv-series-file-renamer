import logging
from PySide6.QtCore import QObject, Signal
from ui.v3.workers.discovery_workers import (
    LanguageFetchWorker, RenameWorker, PlanWorker, 
    UndoWorker, SyncWorker, DataLoader
)
from core.i18n import T

logger = logging.getLogger(__name__)

class DiscoveryController(QObject):
    """
    Handles all business logic for the Discovery Page.
    Decouples UI events from database operations and background workers.
    """
    
    refresh_requested = Signal()
    progress_updated = Signal(int, str)  # value, text
    operation_started = Signal(str)      # message
    operation_finished = Signal(dict)    # results
    error_occurred = Signal(str, str)    # title, message
    
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.active_workers = []

    def split_data(self, videos: list) -> dict:
        """Categorizes raw file data into workspace tabs."""
        # 1. Detect Collisions (Skip Ignored)
        name_map = {} # target_name -> [vids]
        for v in videos:
            if v.get('match_status', '').upper() == 'IGNORED':
                continue
            target = v.get('_new_name')
            if target and target != "-":
                if target not in name_map: name_map[target] = []
                name_map[target].append(v)
        
        # 2. Split Data
        split = {
            "review": [], "movies": [], "shows": [], 
            "extras": [], "dropped": [], "trash": [], 
            "conflicts": []
        }
        
        conflict_ids = set()
        for target, vids in name_map.items():
            if len(vids) > 1:
                for v in vids:
                    v['_is_conflict'] = True 
                    split["conflicts"].append(v)
                    conflict_ids.add(v['id'])

        for v in videos:
            if v['id'] in conflict_ids: continue
                
            status = v.get('match_status', 'pending').upper()
            mtype = v.get('_media_type_from_db') or v.get('fn_media_type')
            cat = v.get('category', 'video')
            
            if status == 'IGNORED': split["trash"].append(v)
            elif v.get('is_manual'): split["dropped"].append(v)
            elif cat != 'video': split["extras"].append(v)
            elif status == 'MATCHED':
                if mtype == 'movie': split["movies"].append(v)
                else: split["shows"].append(v)
            else: split["review"].append(v)
        
        split["conflicts"].sort(key=lambda x: x.get('_new_name', ''))
        return split

    # --- Single Actions ---
    
    def restore_item(self, file_id: int):
        try:
            self.engine.db.update_file(file_id, match_status='PENDING')
            self.refresh_requested.emit()
        except Exception as e:
            self.error_occurred.emit("Database Error", str(e))

    def ignore_item(self, file_id: int):
        try:
            self.engine.db.update_file(file_id, match_status='IGNORED')
            self.refresh_requested.emit()
        except Exception as e:
            self.error_occurred.emit("Database Error", str(e))

    def delete_item(self, file_id: int):
        """Permanently removes an item from the database."""
        try:
            self.engine.db.files.delete_file(file_id)
            self.refresh_requested.emit()
        except Exception as e:
            self.error_occurred.emit("Database Error", str(e))

    def clear_match(self, file_id: int):
        try:
            self.engine.db.matches.clear_all_for_file(file_id)
            self.refresh_requested.emit()
        except Exception as e:
            self.error_occurred.emit("Database Error", str(e))

    # --- Batch Actions ---

    def batch_restore(self, file_ids: list):
        self.operation_started.emit(T("discovery.messages.restoring") if T("discovery.messages.restoring") != "discovery.messages.restoring" else "Restoring items...")
        try:
            for fid in file_ids:
                self.engine.db.update_file(fid, match_status='PENDING')
            self.refresh_requested.emit()
            self.operation_finished.emit({'type': 'batch_update'})
        except Exception as e:
            self.error_occurred.emit("Batch Error", str(e))

    def batch_ignore(self, file_ids: list):
        self.operation_started.emit(T("discovery.messages.ignoring") if T("discovery.messages.ignoring") != "discovery.messages.ignoring" else "Moving items to Trash...")
        try:
            for fid in file_ids:
                self.engine.db.update_file(fid, match_status='IGNORED')
            self.refresh_requested.emit()
            self.operation_finished.emit({'type': 'batch_update'})
        except Exception as e:
            self.error_occurred.emit("Batch Error", str(e))

    def batch_delete(self, file_ids: list):
        """Permanently removes multiple items from the database."""
        self.operation_started.emit(T("discovery.messages.deleting") if T("discovery.messages.deleting") != "discovery.messages.deleting" else "Deleting items...")
        try:
            self.engine.db.files.bulk_delete_files(file_ids)
            self.refresh_requested.emit()
            self.operation_finished.emit({'type': 'batch_update'})
        except Exception as e:
            self.error_occurred.emit("Batch Error", str(e))

    def batch_clear_matches(self, file_ids: list):
        self.operation_started.emit(T("discovery.messages.clearing") if T("discovery.messages.clearing") != "discovery.messages.clearing" else "Resetting identifications...")
        try:
            for fid in file_ids:
                self.engine.db.matches.clear_all_for_file(fid)
            self.refresh_requested.emit()
            self.operation_finished.emit({'type': 'batch_update'})
        except Exception as e:
            self.error_occurred.emit("Batch Error", str(e))

    def batch_organize(self, file_ids: list):
        """Moves files to organized status without physical rename."""
        self.operation_started.emit("Adding items to Library collection...")
        try:
            for fid in file_ids:
                self.engine.db.files.update_file(fid, status='organized')
            self.refresh_requested.emit()
            self.operation_finished.emit({'type': 'batch_update'})
        except Exception as e:
            self.error_occurred.emit("Batch Error", str(e))

    # --- Worker-based Operations ---

    def start_language_fetch(self, item_ids=None):
        self.operation_started.emit("Fetching missing metadata languages...")
        worker = LanguageFetchWorker(self.engine, item_ids)
        self._run_worker(worker, self._on_fetch_finished)

    def start_scan(self, path: str):
        self.operation_started.emit("Starting file discovery pipeline...")
        worker = SyncWorker(self.engine, path)
        self._run_worker(worker, self._on_scan_finished)

    def start_undo(self, batch_id: int):
        self.operation_started.emit("Reverting renames...")
        worker = UndoWorker(self.engine, batch_id)
        self._run_worker(worker, self._on_operation_finished_with_results)

    # --- Internal Worker Helpers ---

    def _run_worker(self, worker, finish_callback):
        # Cleanup finished workers
        self.active_workers = [w for w in self.active_workers if w.isRunning()]
        
        self.active_workers.append(worker)
        worker.progress.connect(self.progress_updated.emit)
        worker.finished.connect(finish_callback)
        worker.start()

    def _on_fetch_finished(self):
        self.operation_finished.emit({'type': 'fetch'})
        self.refresh_requested.emit()

    def _on_scan_finished(self):
        self.operation_finished.emit({'type': 'scan'})
        self.refresh_requested.emit()

    def _on_operation_finished_with_results(self, results):
        self.operation_finished.emit(results)
        self.refresh_requested.emit()

    def abort_all(self):
        for worker in self.active_workers:
            if worker.isRunning():
                worker.stop()
        self.active_workers = []
        self.progress_updated.emit(0, "Operation aborted by user.")

    # --- Data Loading ---

    def refresh_data(self):
        """Triggers a background reload of all discovery data."""
        self.operation_started.emit(T("discovery.messages.refreshing") if T("discovery.messages.refreshing") != "discovery.messages.refreshing" else "Updating your list...")
        worker = DataLoader(self.engine)
        self._run_worker(worker, self._on_data_ready)

    def _on_data_ready(self, videos, poster_paths):
        # Optional prefetch
        if poster_paths:
            from ui.v3.workers.discovery_workers import PosterPrefetcher
            p_worker = PosterPrefetcher(self.engine, poster_paths)
            p_worker.start()
            self.active_workers.append(p_worker)
            
        self.operation_finished.emit({
            'type': 'data_ready',
            'videos': videos,
            'poster_paths': poster_paths
        })

    # --- Rename Pipeline ---

    def start_rename_plan(self, videos: list):
        """Stage 1: Generate a rename plan."""
        self.operation_started.emit("Generating rename plan...")
        worker = PlanWorker(self.engine, videos)
        self._run_worker(worker, self._on_plan_finished)

    def _on_plan_finished(self, plan):
        self.operation_finished.emit({
            'type': 'plan_ready',
            'plan': plan
        })

    def execute_rename(self, plan: list):
        """Stage 2: Execute the approved plan."""
        self.operation_started.emit("Executing renames...")
        worker = RenameWorker(self.engine, plan)
        self._run_worker(worker, self._on_rename_finished)

    def _on_rename_finished(self, results):
        self.refresh_data()
        self.operation_finished.emit({
            'type': 'rename_complete',
            'results': results
        })
