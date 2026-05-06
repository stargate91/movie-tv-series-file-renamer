from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QSize
from ui.v3.styles.theme import Theme
from core.i18n import T

class ResultItemWidget(QWidget):
    """
    Custom widget for displaying a search result in the list with a small icon and metadata.
    """
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        # 1. Icon / Indicator
        icon_lbl = QLabel()
        m_type = self.data.get('media_type', 'movie')
        if m_type == 'tv': icon_text = "📺"
        elif m_type == 'season': icon_text = "📂"
        elif m_type == 'episode': icon_text = "📄"
        else: icon_text = "🎬"
        
        icon_lbl.setText(icon_text)
        icon_lbl.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_lbl)

        # 2. Text Info
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        title = QLabel(self.data.get('title', T("common.unknown")))
        title.setStyleSheet(Theme.get_result_item_title_style())
        text_layout.addWidget(title)
        
        meta_text = T(f"common.types.{m_type}") if T(f"common.types.{m_type}") != f"common.types.{m_type}" else m_type.capitalize()
        if self.data.get('year'): meta_text += f" • {self.data['year']}"
        if self.data.get('episode_count'): 
            count = self.data['episode_count']
            meta_text += f" • {T('common.episodes', count=count)}"
        
        meta = QLabel(meta_text)
        meta.setStyleSheet(Theme.get_result_item_meta_style())
        text_layout.addWidget(meta)
        
        layout.addLayout(text_layout)
        layout.addStretch()
