from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from utils.cache import MediaCache

# Global caches
IMAGE_CACHE = {} # Memory cache (pixmaps)
MEDIA_STORE = MediaCache() # SQL cache (blobs)

class PosterPopup(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setStyleSheet("border: 2px solid #0078d4; background-color: #000000; border-radius: 8px;")
        self.setFixedSize(300, 450)
        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self.on_finished)
        self.current_url = None

    def load(self, url):
        if not url: return
        self.current_url = url
        
        # 1. Memory Cache
        if url in IMAGE_CACHE:
            self.setPixmap(IMAGE_CACHE[url].scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return

        # 2. SQL Cache
        blob = MEDIA_STORE.get_image(url)
        if blob:
            pixmap = QPixmap()
            pixmap.loadFromData(blob)
            IMAGE_CACHE[url] = pixmap
            self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return

        # 3. Network
        self.manager.get(QNetworkRequest(QUrl(url)))

    def on_finished(self, reply):
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            url = reply.url().toString()
            
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            
            IMAGE_CACHE[url] = pixmap
            MEDIA_STORE.set_image(url, bytes(data)) # Save to SQL
            
            if url == self.current_url:
                self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

class ImageLoader(QLabel):
    def __init__(self, url, width=40, height=60):
        super().__init__()
        self.url = url
        self.setFixedSize(width, height)
        self.setStyleSheet("background-color: #e5e7eb; border-radius: 4px;")
        self.setAlignment(Qt.AlignCenter)
        self.setText("...")
        self.popup = None
        
        if not url:
            self.setText("?")
            return

        # 1. Memory Cache
        if url in IMAGE_CACHE:
            self.set_pix(IMAGE_CACHE[url])
            return
        
        # 2. SQL Cache
        blob = MEDIA_STORE.get_image(url)
        if blob:
            pixmap = QPixmap()
            pixmap.loadFromData(blob)
            IMAGE_CACHE[url] = pixmap
            self.set_pix(pixmap)
            return

        # 3. Network
        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self.on_finished)
        self.manager.get(QNetworkRequest(QUrl(url)))

    def set_pix(self, pixmap):
        self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.setText("")

    def on_finished(self, reply):
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            
            IMAGE_CACHE[self.url] = pixmap
            MEDIA_STORE.set_image(self.url, bytes(data)) # Save to SQL
            
            self.set_pix(pixmap)
        else:
            self.setText("?")
            self.setAlignment(Qt.AlignCenter)

    def enterEvent(self, event):
        if self.url:
            if not self.popup:
                self.popup = PosterPopup()
                hd_url = self.url.replace("/w200/", "/w500/")
                self.popup.load(hd_url)
            pos = self.mapToGlobal(self.rect().topRight())
            self.popup.move(pos.x() + 10, pos.y() - 100)
            self.popup.show()

    def leaveEvent(self, event):
        if self.popup:
            self.popup.hide()
