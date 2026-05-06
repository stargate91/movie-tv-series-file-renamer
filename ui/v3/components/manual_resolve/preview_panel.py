from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from ui.v3.styles.theme import Theme
from core.i18n import T

class PreviewPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(Theme.get_preview_panel_style())
        self.setFixedWidth(280)
        layout = QVBoxLayout(self)
        
        self.poster = QLabel(T("manual_resolve.no_selection"))
        self.poster.setAlignment(Qt.AlignCenter)
        self.poster.setFixedSize(250, 375)
        self.poster.setStyleSheet(Theme.get_batch_card_style())
        
        self.title = QLabel(T("discovery.manual_resolve.select_result"))
        self.title.setWordWrap(True)
        self.title.setStyleSheet(Theme.get_preview_title_style())
        
        self.meta = QLabel("")
        self.meta.setStyleSheet(Theme.get_preview_meta_style())
        
        self.overview = QLabel("")
        self.overview.setWordWrap(True)
        self.overview.setStyleSheet(Theme.get_preview_overview_style())
        
        layout.addWidget(self.poster, 0, Qt.AlignCenter)
        layout.addWidget(self.title)
        layout.addWidget(self.meta)
        layout.addWidget(self.overview)
        layout.addStretch()

    def update_info(self, res):
        self.title.setText(res['title'])
        meta = T("manual_resolve.type_label", type=res['media_type'].capitalize())
        if res.get('year'): meta += f" • {res['year']}"
        
        # Add Network info if available
        network = res.get('networks')
        if not network and res.get('details_json'):
            try:
                import json
                details = json.loads(res['details_json'])
                if details.get('networks'):
                    network = ", ".join([n['name'] for n in details['networks']])
            except: pass
            
        if network:
            meta += f"\n{network}"
            
        if res.get('collection'):
            meta += f"\nCollection: {res['collection']}"
            
        self.meta.setText(meta)
        self.overview.setText(res.get('overview', ""))
        
    def set_poster(self, pixmap):
        if not pixmap or pixmap.isNull():
            self.poster.setPixmap(QPixmap())
            self.poster.setText(T("manual_resolve.no_poster"))
        else:
            scaled = pixmap.scaled(self.poster.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.poster.setPixmap(scaled)

    def set_loading(self):
        self.poster.setPixmap(QPixmap())
        self.poster.setText(T("common.loading"))
