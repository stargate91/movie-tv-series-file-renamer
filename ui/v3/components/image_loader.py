import os
import requests
from PySide6.QtCore import QRunnable, QObject, Signal, QThreadPool
from PySide6.QtGui import QPixmap

class ImageLoaderSignals(QObject):
    finished = Signal(QPixmap)

class ImageLoader(QRunnable):
    """
    Downloads an image from a URL and emits a QPixmap via signals.
    Designed to run in a QThreadPool to prevent thread exhaustion.
    """
    def __init__(self, url, cache_path=None):
        super().__init__()
        self.url = url
        self.cache_path = cache_path
        self.signals = ImageLoaderSignals()
        self.is_killed = False

    def stop(self):
        self.is_killed = True

    def run(self):
        try:
            if self.is_killed: return
            
            # 1. Check cache first
            if self.cache_path and os.path.exists(self.cache_path):
                pixmap = QPixmap(self.cache_path)
                if not self.is_killed:
                    self.signals.finished.emit(pixmap)
                return

            # 2. Download (use a simple requests call, session is overkill here for single runs)
            response = requests.get(self.url, timeout=10)
            if self.is_killed: return
            
            if response.status_code == 200:
                data = response.content
                
                # 3. Save to cache
                if self.cache_path and not self.is_killed:
                    try:
                        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
                        with open(self.cache_path, 'wb') as f:
                            f.write(data)
                    except: pass
                
                if self.is_killed: return
                
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                if not self.is_killed:
                    self.signals.finished.emit(pixmap)
            else:
                if not self.is_killed:
                    self.signals.finished.emit(QPixmap())
        except Exception:
            if not self.is_killed:
                self.signals.finished.emit(QPixmap())
