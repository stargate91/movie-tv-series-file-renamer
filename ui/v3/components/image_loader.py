import os
import requests
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap

class ImageDownloader(QThread):
    """Downloads an image from a URL and emits a QPixmap."""
    finished = Signal(QPixmap)

    def __init__(self, url, cache_path=None, session=None):
        super().__init__()
        self.url = url
        self.cache_path = cache_path
        self.session = session or requests.Session()

    def run(self):
        try:
            # Check cache first
            if self.cache_path and os.path.exists(self.cache_path):
                pixmap = QPixmap(self.cache_path)
                self.finished.emit(pixmap)
                return

            # Download
            response = self.session.get(self.url, timeout=10)
            if response.status_code == 200:
                data = response.content
                
                # Save to cache if provided
                if self.cache_path:
                    os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
                    with open(self.cache_path, 'wb') as f:
                        f.write(data)
                
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                self.finished.emit(pixmap)
            else:
                self.finished.emit(QPixmap())
        except Exception:
            self.finished.emit(QPixmap())
