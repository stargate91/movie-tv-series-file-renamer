import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, 
                             QSizePolicy, QGraphicsDropShadowEffect, QMenu)
from PySide6.QtCore import Qt, QSize, Signal, QThreadPool
from PySide6.QtGui import QPixmap, QColor, QCursor
from ui.v3.styles.theme import Theme
from core.i18n import T

class PosterWidget(QFrame):
    """A card displaying a movie/series poster with title."""
    clicked = Signal(dict) # Emits the full file data
    send_back_requested = Signal(int) # Emits file_id
    refresh_requested = Signal(dict) # Emits the full data for refreshing

    def __init__(self, data, target_lang=None, parent=None):
        super().__init__(parent)
        self.data = data
        self.target_lang = target_lang
        self.loader = None
        self._init_ui()

    def _init_ui(self):
        # Determine if this is an episode (Landscape) or Movie/Series (Portrait)
        self.is_episode = bool(self.data.get('episode_poster') or self.data.get('episode_title'))
        
        # Adjust widget size based on content
        h = 160 if self.is_episode else 280
        self.setFixedSize(160, h)
        
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
        if self.is_episode:
            self.poster_lbl.setFixedSize(160, 90) # 16:9 approx
        else:
            self.poster_lbl.setFixedSize(160, 230) # Portrait
            
        self.poster_lbl.setScaledContents(False)
        self.poster_lbl.setAlignment(Qt.AlignCenter)
        self.poster_lbl.setStyleSheet(f"border-top-left-radius: 10px; border-top-right-radius: 10px; border: none; background: #000;")
        
        self._load_poster()
        layout.addWidget(self.poster_lbl)

        # 2. Title Label (Localized)
        title_text = self._get_localized_title()
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet(f"color: {Theme.TEXT_MAIN}; font-size: 11px; font-weight: 700; padding: 5px;")
        layout.addWidget(self.title_lbl)
        
    def _get_localized_title(self):
        """Extracts title in target_lang if available in details_json."""
        import json
        lang = self.target_lang
        
        # Priority: Episode -> Season -> Media
        keys = [
            ('episode_details', 'name'),
            ('season_details', 'name'),
            ('media_details', 'title' if self.data.get('media_item_type') == 'movie' else 'name')
        ]
        
        for data_key, field_name in keys:
            json_str = self.data.get(data_key)
            if json_str and lang:
                try:
                    details = json.loads(json_str)
                    if lang in details and details[lang].get(field_name):
                        return details[lang][field_name]
                except: pass
        
        # Fallback to main columns
        return (self.data.get('episode_title') or 
                self.data.get('season_name') or 
                self.data.get('media_title') or 
                self.data.get('file_name') or "Unknown")

    def _load_poster(self):
        # Order of preference: Episode still -> Season poster -> Media (Movie/Series) poster
        import json
        ep_still = self.data.get('episode_poster')
        if not ep_still and self.data.get('episode_details'):
            try:
                details = json.loads(self.data['episode_details'])
                # Try target lang, then any available lang
                if self.target_lang and self.target_lang in details:
                    ep_still = details[self.target_lang].get('still_path')
                if not ep_still:
                    for l in details.values():
                        if isinstance(l, dict) and l.get('still_path'):
                            ep_still = l['still_path']
                            break
            except: pass

        posters = [
            ep_still,
            self.data.get('season_poster'),
            self.data.get('media_poster')
        ]
        
        target_path = None
        for i, p in enumerate(posters):
            if not p: continue
            local_path = self._get_local_path(p)
            if os.path.exists(local_path):
                pix = QPixmap(local_path)
                self._set_pixmap_scaled(pix)
                return
            if not target_path:
                target_path = p

        if target_path:
            # Stop existing loader if any
            if self.loader:
                self.loader.stop()
                try: self.loader.signals.finished.disconnect()
                except: pass
            
            url = f"https://image.tmdb.org/t/p/w500{target_path}"
            local_path = self._get_local_path(target_path)
            from ui.v3.components.image_loader import ImageLoader
            self.loader = ImageLoader(url, cache_path=local_path)
            self.loader.signals.finished.connect(self._on_poster_downloaded)
            QThreadPool.globalInstance().start(self.loader)
        else:
            self._show_placeholder()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(Theme.get_context_menu_style())
        
        refresh_act = menu.addAction(T("library.actions.refresh_metadata") if T("library.actions.refresh_metadata") != "library.actions.refresh_metadata" else "Refresh Metadata")
        refresh_act.triggered.connect(lambda: self.refresh_requested.emit(self.data))
        
        menu.exec(event.globalPos())

    def _on_poster_downloaded(self, pixmap):
        if not pixmap.isNull():
            self._set_pixmap_scaled(pixmap)
        else:
            self._show_placeholder()
        self.loader = None

    def _set_pixmap_scaled(self, pix):
        """Scales pixmap based on orientation while preserving quality."""
        size = self.poster_lbl.size()
        scaled = pix.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        # Center crop to fit the label
        final = scaled.copy(
            (scaled.width() - size.width()) // 2,
            (scaled.height() - size.height()) // 2,
            size.width(),
            size.height()
        )
        self.poster_lbl.setPixmap(final)

    def __del__(self):
        """Cleanup on destruction."""
        if hasattr(self, 'loader') and self.loader:
            self.loader.stop()
            try: self.loader.signals.finished.disconnect()
            except: pass

    def _show_placeholder(self):
        placeholder = Theme.get_pixmap("movie", size=64, color=Theme.TEXT_DIM)
        self.poster_lbl.setPixmap(placeholder)
        self.poster_lbl.setStyleSheet("background: #1e293b; border-top-left-radius: 10px; border-top-right-radius: 10px;")

    def _get_local_path(self, tmdb_path):
        """Converts a TMDB path to a local cache path."""
        if not tmdb_path: return ""
        # Base dir is the project root (3 levels up from ui/v3/components)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_path = os.path.join(base_dir, 'data', 'cache', 'posters', tmdb_path.lstrip('/'))
        return os.path.normpath(cache_path)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.data)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(Theme.get_context_menu_style())
        
        open_act = menu.addAction(Theme.get_icon("folder", size=16, color=Theme.TEXT_MAIN), T("library.open_folder") or "Show in Folder")
        send_back_act = menu.addAction(Theme.get_icon("undo", size=16, color=Theme.TEXT_MAIN), T("library.send_back") or "Send back to Workspace")
        
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
