import logging
from PySide6.QtCore import QThread, Signal
from ui.ui_interface import UIInterface

logger = logging.getLogger(__name__)

class WorkerThread(QThread):
    def __init__(self, target_func):
        super().__init__()
        self.target_func = target_func

    def run(self):
        try:
            print(f"DEBUG: WorkerThread starting: {self.target_func}")
            self.target_func()
            print("DEBUG: WorkerThread finished successfully.")
        except Exception as e:
            print(f"CRITICAL: Worker thread crashed: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Worker thread error: {e}")

class QtUIBridge(UIInterface):
    """Bridges the backend pipeline to the Qt UI using signals."""
    def __init__(self, main_window):
        self.mw = main_window

    def update_progress(self, current, total, status=None):
        self.mw.progress_signal.emit(current, total, status)

    def show_message(self, message, level="info"):
        print(f"[{level.upper()}] {message}")

    def ask_decision(self, title, message):
        return True # Default to yes for now

    def ask_input(self, title, message):
        return ""

    def ask_selection(self, title, options):
        return None

    def prompt_user_choice(self, title, options):
        pass
