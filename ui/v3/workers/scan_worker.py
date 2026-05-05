import logging
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

class ScanWorker(QThread):
    """
    Background worker for scanning, collecting local metadata, and identifying media.
    Orchestrates the full discovery pipeline.
    """
    progress = Signal(int, str) # progress_percent, status_text
    finished = Signal()

    def __init__(self, engine, path):
        super().__init__()
        self.engine = engine
        self.path = path

    def run(self):
        try:
            # 1. Phase: Scanning (0-20%)
            def scan_cb(text, current, total):
                if total > 0:
                    pct = int((current / total) * 20)
                    self.progress.emit(pct, f"[{current}/{total}] {text}")

            self.engine.scanner.scan_directory(self.path, progress_callback=scan_cb)
            
            # 2. Phase: Collecting Local Metadata (20-50%)
            def collect_cb(text, current, total):
                if total > 0:
                    pct = 20 + int((current / total) * 30)
                    self.progress.emit(pct, f"[{current}/{total}] {text}")
                else:
                    self.progress.emit(50, "No metadata to collect.")

            self.engine.collector.collect_all(progress_callback=collect_cb)
            
            # 3. Phase: Identifying Media via APIs (50-100%)
            def resolve_cb(text, current, total):
                if total > 0:
                    pct = 50 + int((current / total) * 50)
                    self.progress.emit(pct, f"[{current}/{total}] {text}")
                else:
                    self.progress.emit(100, "No media to identify.")

            self.engine.resolver.resolve_all(progress_callback=resolve_cb)
            
            self.progress.emit(100, "Discovery complete.")
            self.finished.emit()
            
        except Exception as e:
            logger.error(f"ScanWorker Error: {e}")
            self.progress.emit(0, f"Error: {str(e)}")
            self.finished.emit()
