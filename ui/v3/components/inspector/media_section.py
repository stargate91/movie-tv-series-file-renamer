from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFontMetrics
from ui.v3.styles.theme import Theme
from core.i18n import T

class ElidedLabel(QLabel):
    """Custom label that elides text with '...' if it's too long for the available space."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumWidth(1) # Allow it to shrink
        self._full_text = text

    def setText(self, text):
        self._full_text = text
        self._update_elision()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elision()

    def _update_elision(self):
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, Qt.ElideRight, self.width())
        super().setText(elided)
        self.setToolTip(self._full_text if elided != self._full_text else "")

class MediaSection(QWidget):
    """
    Main section for media metadata (Title, Year, Overview, Episode info).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)

        # Labels for the vertical stack (Each is one line, elided if too long)
        self.lbl_main = ElidedLabel("")
        self.lbl_main.setStyleSheet(Theme.get_inspector_title_style())
        self.content_layout.addWidget(self.lbl_main)

        self.lbl_year = ElidedLabel("")
        self.lbl_year.setStyleSheet(Theme.get_inspector_year_style())
        self.content_layout.addWidget(self.lbl_year)

        self.lbl_id = ElidedLabel("")
        self.lbl_id.setStyleSheet(Theme.get_inspector_ep_id_style())
        self.content_layout.addWidget(self.lbl_id)

        self.lbl_sub = ElidedLabel("")
        self.lbl_sub.setStyleSheet(Theme.get_inspector_ep_title_style())
        self.content_layout.addWidget(self.lbl_sub)

        # Overview Section
        self.overview_lbl = QLabel(T("discovery.inspector.empty.overview"))
        self.overview_lbl.setWordWrap(True)
        self.overview_lbl.setStyleSheet(Theme.get_inspector_overview_style())
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(Theme.get_scroll_area_style())
        scroll.setWidget(self.overview_lbl)
        self.content_layout.addWidget(scroll, 1)

    def update_unmatched(self, file_data):
        if not file_data: return
        self.clear()
        self.lbl_main.setText(file_data.get('file_name', T("common.none")))
        self.lbl_main.show()
        self.overview_lbl.setText(T("discovery.inspector.empty.overview"))

    def update_movie(self, media_data):
        if not media_data: return
        self.clear()
        self.lbl_main.setText(media_data.get('title', T("common.none")))
        self.lbl_main.show()
        year = str(media_data.get('year', ''))
        self.lbl_year.setText(year)
        self.lbl_year.setVisible(bool(year))
        self.overview_lbl.setText(media_data.get('overview', T("discovery.inspector.empty.overview")))

    def update_episode(self, media_data, ep_data_list):
        if not media_data or not ep_data_list: return
        self.clear()
        if not isinstance(ep_data_list, list): ep_data_list = [ep_data_list]
        
        # 1. Series Title
        self.lbl_main.setText(media_data.get('title', ''))
        self.lbl_main.show()
        
        # 2. Episode Year
        year = ep_data_list[0].get('air_date', '')[:4] or str(media_data.get('year', ''))
        self.lbl_year.setText(year)
        self.lbl_year.setVisible(bool(year))
        
        # 3. S/E (IDs)
        ids = []
        ep_titles = []
        for ep in ep_data_list:
            s = ep.get('season_number', '?')
            e = ep.get('episode_number', '?')
            ids.append(f"S{str(s).zfill(2)}E{str(e).zfill(2)}")
            if ep.get('name'):
                ep_titles.append(ep.get('name'))
        
        self.lbl_id.setText(", ".join(ids))
        self.lbl_id.setVisible(bool(ids))
        
        # 4. Episode Title
        self.lbl_sub.setText(" / ".join(ep_titles))
        self.lbl_sub.setVisible(bool(ep_titles))
        self.overview_lbl.setText(media_data.get('overview', T("discovery.inspector.empty.overview")))

    def update_status(self, status):
        # Now handled by PosterCarousel
        pass

    def clear(self):
        self.lbl_main.setText("")
        self.lbl_main.hide()
        self.lbl_year.setText("")
        self.lbl_year.hide()
        self.lbl_id.setText("")
        self.lbl_id.hide()
        self.lbl_sub.setText("")
        self.lbl_sub.hide()
        self.overview_lbl.setText(T("discovery.inspector.empty.overview"))

