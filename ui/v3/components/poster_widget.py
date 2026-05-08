import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, 
                             QSizePolicy, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPixmap, QColor, QCursor
from ui.v3.styles.theme import Theme

class PosterWidget(QFrame):
    """A card displaying a movie/series poster with title."""
    clicked = Signal(dict) # Emits the full file data
    send_back_requested = Signal(int) # Emits file_id

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._init_ui()

    def _init_ui(self):
        self.setFixedSize(160, 280)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("PosterCard")
        self.setStyleSheet(f"""
            #PosterCard {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
            }}
            #PosterCard:hover {{
                background-color: {Theme.SURFACE_LIGHT};
                border-color: {Theme.PRIMARY};
            }}
        """)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(8)

        # 1. Poster Image
        self.poster_lbl = QLabel()
        self.poster_lbl.setFixedSize(160, 230)
        self.poster_lbl.setScaledContents(True)
        self.poster_lbl.setAlignment(Qt.AlignCenter)
        self.poster_lbl.setStyleSheet("border-top-left-radius: 10px; border-top-right-radius: 10px; border: none; background: #000;")
        
        self._load_poster()
        layout.addWidget(self.poster_lbl)

        # 2. Title Label
        title_text = self.data.get('media_title') or self.data.get('file_name')
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet(f"color: {Theme.TEXT_MAIN}; font-size: 11px; font-weight: 700; padding: 0 5px;")
        layout.addWidget(self.title_lbl)
        
        layout.addStretch()

    def _load_poster(self):
        # 1. Try local cache
        poster_path = self.data.get('media_poster')
        if poster_path and os.path.exists(poster_path):
            self.poster_lbl.setPixmap(QPixmap(poster_path))
        else:
            # Fallback or placeholder
            placeholder = Theme.get_pixmap("movie", size=64, color=Theme.TEXT_DIM)
            self.poster_lbl.setPixmap(placeholder)
            self.poster_lbl.setStyleSheet("background: #1e293b; border-top-left-radius: 10px; border-top-right-radius: 10px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.data)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(Theme.get_context_menu_style())
        
        open_act = menu.addAction(Theme.get_icon("folder", size=16, color=Theme.TEXT_MAIN), T("library.open_folder"))
        send_back_act = menu.addAction(Theme.get_icon("undo", size=16, color=Theme.TEXT_MAIN), T("library.send_back"))
        
        action = menu.exec(QCursor.pos())
        
        if action == open_act:
            self._on_open_folder()
        elif action == send_back_act:
            self._on_send_back()

    def _on_open_folder(self):
        path = self.data.get('current_path')
        if path and os.path.exists(path):
            import subprocess
            if os.name == 'nt':
                os.startfile(os.path.dirname(path))
            else:
                subprocess.run(['open', os.path.dirname(path)])

    def _on_send_back(self):
        self.send_back_requested.emit(self.data['id'])
