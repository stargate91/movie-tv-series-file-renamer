from PySide6.QtCore import QObject, Signal
from ui.utils import WorkerThread

class TaskCoordinator(QObject):
    """
    Manages background tasks and worker threads.
    Decouples task execution from the UI.
    """
    task_started = Signal(str)    # task_name
    task_finished = Signal(str)   # task_name
    error_occurred = Signal(str)  # error_msg

    def __init__(self, window, pipeline, state):
        super().__init__()
        self.window = window
        self.pipeline = pipeline
        self.state = state
        self.active_worker = None

    def run_task(self, task_id, func, on_finished=None):
        """Generic runner for background tasks."""
        if self.active_worker and self.active_worker.isRunning():
            return False # Avoid parallel tasks of the same type if needed
            
        self.task_started.emit(task_id)
        
        self.active_worker = WorkerThread(func)
        if on_finished:
            self.active_worker.finished.connect(on_finished)
        
        self.active_worker.finished.connect(lambda: self.task_finished.emit(task_id))
        self.active_worker.start()
        return True

    def start_scan(self):
        def run_logic():
            # In coordinator, we handle the setup
            from utils.api_client import APIClient
            from core.pipeline import RenamePipeline
            from ui.utils import QtUIBridge
            
            bridge = QtUIBridge(self.window)
            api = APIClient(self.window.cfg.settings.omdb_key, self.window.cfg.settings.tmdb_key, self.window.cfg.settings.tmdb_bearer_token)
            self.pipeline = RenamePipeline(self.window.cfg, api, bridge, self.state)
            self.window.pipeline = self.pipeline
            self.window.list_mgr.pipeline = self.pipeline
            from ui.controllers.main_controller import MainController
            if not self.window.ctrl:
                self.window.ctrl = MainController(self.window, self.pipeline, self.state)
            else:
                self.window.ctrl.pipeline = self.pipeline
            
            self.pipeline.step_1_collect_files()

        self.run_task('scan', run_logic, self.window.on_scan_finished)

    def start_unified_analysis(self):
        self.run_task(
            'unified_analysis', 
            self.pipeline.unified_analysis, 
            self.window.on_scan_finished
        )

    def start_renaming(self):
        # The renaming logic requires a confirmation check sometimes, 
        # but the physical execution can be wrapped.
        def rename_wrapper():
            self.pipeline.step_5_rename()
            
        self.run_task(
            'renaming', 
            rename_wrapper, 
            self.window.on_rename_finished
        )

    def trigger_enrichment(self, items_to_enrich):
        def run_enrich():
            # In modular pipeline, we might need a specific way to set items
            # For now, keeping parity with existing logic
            if hasattr(self.pipeline, 'collected_results'):
                self.pipeline.collected_results = items_to_enrich
            self.pipeline.step_4_standardize_and_enrich()
            
        self.run_task(
            'enrichment', 
            run_enrich, 
            self.window.on_enrichment_finished
        )
