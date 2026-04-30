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
            self.target_func()
        except Exception as e:
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
