from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# Global cache for posters
IMAGE_CACHE = {}

class PosterPopup(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setStyleSheet("border: 2px solid #0078d4; background-color: #000000; border-radius: 8px;")
        self.setFixedSize(300, 450)
        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self.on_finished)

    def load(self, url):
        if not url: return
        if url in IMAGE_CACHE:
            self.setPixmap(IMAGE_CACHE[url].scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return
        self.manager.get(QNetworkRequest(QUrl(url)))

    def on_finished(self, reply):
        if reply.error() == QNetworkReply.NoError:
            pixmap = QPixmap()
            pixmap.loadFromData(reply.readAll())
            IMAGE_CACHE[reply.url().toString()] = pixmap
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
        
        if url in IMAGE_CACHE:
            self.set_pix(IMAGE_CACHE[url])
            return

        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self.on_finished)
        if url:
            self.manager.get(QNetworkRequest(QUrl(url)))

    def set_pix(self, pixmap):
        self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.setText("")

    def on_finished(self, reply):
        if reply.error() == QNetworkReply.NoError:
            pixmap = QPixmap()
            pixmap.loadFromData(reply.readAll())
            IMAGE_CACHE[self.url] = pixmap
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
