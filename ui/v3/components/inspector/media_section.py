import json
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
        self._preferred_language = "en-US"
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

    def update_uncertain(self, candidates):
        """Displays a notice when multiple candidates are available for a file."""
        if not candidates: return
        self.clear()
        
        count = len(candidates)
        self.lbl_main.setText(T("discovery.messages.uncertain_title") if T("discovery.messages.uncertain_title") != "discovery.messages.uncertain_title" else "Ambiguous Match")
        self.lbl_main.show()
        
        self.lbl_sub.setText(T("discovery.messages.uncertain_count", count=count) if T("discovery.messages.uncertain_count", count=count) != "discovery.messages.uncertain_count" else f"{count} potential matches found")
        self.lbl_sub.show()
        
        msg = T("discovery.messages.uncertain_msg") if T("discovery.messages.uncertain_msg") != "discovery.messages.uncertain_msg" else "This file has multiple potential matches. Click 'Fix' to manually select the correct one."
        self.overview_lbl.setText(msg)

    def update_unmatched(self, file_data):
        if not file_data: return
        self.clear()
        self.lbl_main.setText(file_data.get('file_name', T("common.none")))
        self.lbl_main.show()
        self.overview_lbl.setText(T("discovery.inspector.empty.overview"))

    def update_movie(self, media_data):
        if not media_data: return
        self.clear()
        
        title = self._get_translated(media_data, 'title', T("common.none"))
        overview = self._get_translated(media_data, 'overview', T("discovery.inspector.empty.overview"))
        
        self.lbl_main.setText(title)
        self.lbl_main.show()
        year = str(media_data.get('year', ''))
        self.lbl_year.setText(year)
        self.lbl_year.setVisible(bool(year))
        self.overview_lbl.setText(overview)

    def update_episode(self, media_data, ep_data_list):
        if not media_data: return
        self.clear()
        if not ep_data_list:
            # Fallback to series info if no episodes linked
            self.update_movie(media_data)
            return
            
        if not isinstance(ep_data_list, list): ep_data_list = [ep_data_list]
        
        # 1. Series Title
        title = self._get_translated(media_data, 'title', '')
        self.lbl_main.setText(title)
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
            
            ep_title = self._get_translated(ep, 'name')
            if ep_title:
                ep_titles.append(ep_title)
        
        self.lbl_id.setText(", ".join(ids))
        self.lbl_id.setVisible(bool(ids))
        
        # 4. Episode Title
        self.lbl_sub.setText(" / ".join(ep_titles))
        self.lbl_sub.setVisible(bool(ep_titles))
        
        # 5. Overview (Use episode overview if single, otherwise show series overview)
        if len(ep_data_list) == 1:
            ep_ov = self._get_translated(ep_data_list[0], 'overview')
            if ep_ov:
                self.overview_lbl.setText(ep_ov)
            else:
                self.overview_lbl.setText(self._get_translated(media_data, 'overview', T("discovery.inspector.empty.overview")))
        else:
            self.overview_lbl.setText(self._get_translated(media_data, 'overview', T("discovery.inspector.empty.overview")))

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

    def set_preferred_language(self, lang):
        self._preferred_language = lang

    def _get_translated(self, data, field, default=""):
        if not data: return default
        details_json = data.get('details_json')
        
        # 1. Try from localized JSON store
        if details_json:
            try:
                details = json.loads(details_json)
                if isinstance(details, dict):
                    # Robust language lookup: try exact match, then 2-letter prefix
                    lang_key = self._preferred_language
                    if lang_key not in details:
                        lang_key = lang_key.split('-')[0]
                    
                    if lang_key in details:
                        lang_data = details[lang_key]
                        # TMDB uses 'name' for TV/Episodes and 'title' for Movies
                        if field in ('title', 'name'):
                            val = lang_data.get('title') or lang_data.get('name')
                        else:
                            val = lang_data.get(field)
                        if val: return val
            except: pass
        
        # 2. Fallback to column data (usually original or first-fetched language)
        if field in ('title', 'name'):
            return data.get('title') or data.get('name') or default
        return data.get(field, default)

