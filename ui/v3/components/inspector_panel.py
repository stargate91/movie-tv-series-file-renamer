import os
import logging
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QWidget, QScrollArea
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal

from ui.v3.styles.theme import Theme
from .inspector.poster_carousel import PosterCarousel
from .inspector.media_section import MediaSection
from .inspector.technical_section import TechnicalSection
from .inspector.data_sheet import DataSheetDialog
from core.i18n import T

logger = logging.getLogger(__name__)

class InspectorPanel(QFrame):
    """
    Right-side panel orchestrator.
    Decomposed into specialized sections for Posters, Media Metadata, and Technical Info.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(340)
        self.setObjectName("Inspector")
        self.setStyleSheet(Theme.get_inspector_style())
        self._current_file_data = None
        self._current_media_data = None
        self._current_episode_data = None
        self._current_season_data = None
        self._preferred_language = "en-US"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Scroll Area for all content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        container = QWidget()
        container.setObjectName("InspectorContainer")
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(10)
        self.content_layout.setAlignment(Qt.AlignTop)

        # 1. Poster Carousel
        self.poster_carousel = PosterCarousel()
        self.content_layout.addWidget(self.poster_carousel, alignment=Qt.AlignHCenter)

        # 2. Media Metadata Section
        self.media_section = MediaSection()
        self.content_layout.addWidget(self.media_section)

        # 3. Technical Section
        self.tech_section = TechnicalSection()
        self.content_layout.addWidget(self.tech_section)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # 4. Check Data Button (Keep at bottom)
        self.data_btn = QPushButton(T("discovery.inspector.check_data"))
        self.data_btn.setFixedHeight(40)
        self.data_btn.setCursor(Qt.PointingHandCursor)
        self.data_btn.setStyleSheet(Theme.get_secondary_ghost_button_style())
        self.data_btn.clicked.connect(self._on_check_data_clicked)
        
        btn_container = QWidget()
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.setContentsMargins(20, 10, 20, 20)
        btn_layout.addWidget(self.data_btn)
        layout.addWidget(btn_container)

    def set_empty(self):
        self._current_file_data = None
        self._current_media_data = None
        self._current_episode_data = None
        self._current_season_data = None
        self._current_children = []
        
        self.poster_carousel.clear()
        self.media_section.clear()
        self.tech_section.clear()

    def set_file(self, file_id: int, engine):
        """Main entry point to update inspector content based on a selection."""
        self.set_empty()
        if not file_id: return
        
        # 1. Get Core File Data
        file_data = engine.db.files.get_file_by_id(file_id)
        if not file_data: return
        
        self._current_file_data = file_data
        self.update_tech_info(file_data)
        
        # 2. Get Media Links
        links = engine.db.media.get_links_for_file(file_id)
        if not links:
            # Check for multiple candidates
            candidates = engine.db.matches.get_candidates(file_id)
            if candidates:
                self.media_section.update_uncertain(candidates)
            return

        # 3. Process first matched link
        link = links[0]
        media_id = link.get('media_item_id')
        
        # 4. Fetch Detailed Metadata
        media_data = engine.db.media.get_media_item_by_id(media_id)
        if not media_data: return
        
        mtype = media_data.get('media_type')
        self._current_media_data = media_data
        self.update_from_data(media_data)
        
        # 5. Handle Episode/Series Hierarchy
        if mtype == 'tv':
            series_pix = self._load_pixmap(self._get_translated(media_data, 'poster_path'))
            season_pix = None
            all_episode_pix = []
            
            # Get Episode Details
            ep_links = [l for l in links if l.get('tv_episode_id')]
            ep_data = []
            season_data = None
            
            for el in ep_links:
                ed = engine.db.media.get_episode_by_id(el['tv_episode_id'])
                if ed:
                    ep_data.append(ed)
                    p_ep = self._load_pixmap(self._get_translated(ed, 'still_path', ed.get('still_path')))
                    if p_ep: all_episode_pix.append(p_ep)
                    
                    if not season_data:
                        season_data = engine.db.media.get_season_for_episode(el['tv_episode_id'])
            
            # Fallback for season
            if not season_data:
                try:
                    s_num = file_data.get('fn_season') if file_data.get('fn_season') is not None else file_data.get('fd_season')
                    if s_num is not None:
                        season_data = engine.db.media.get_season_by_number(media_data['id'], int(s_num))
                except: pass
                
            if season_data:
                season_pix = self._load_pixmap(self._get_translated(season_data, 'poster_path'))
                self.update_episode_info(ep_data, season_data)
            else:
                self.update_episode_info(ep_data)

            self.poster_carousel.set_tv_posters(series_pix, season_pix, *all_episode_pix)
        else:
            # Movie Poster
            pix = self._load_pixmap(self._get_translated(media_data, 'poster_path'))
            self.poster_carousel.set_single_poster(pix)

        # 6. Fetch Linked Children (Extras, Subs)
        self._current_children = engine.db.files.get_children(file_id)

    def _load_pixmap(self, poster_path):
        if not poster_path: return None
        # Root path resolution
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        local_path = os.path.join(base_dir, 'data', 'cache', 'posters', poster_path.lstrip('/'))
        if os.path.exists(local_path):
            return QPixmap(local_path)
        return None

    def update_status(self, status):
        # MediaSection.update_status is now a no-op as logic moved to poster
        self.media_section.update_status(status)

    def update_from_data(self, media_data):
        self._current_media_data = media_data
        
        # Reload posters for current language
        if media_data.get('media_type') == 'movie':
            pix = self._load_pixmap(self._get_translated(media_data, 'poster_path'))
            self.poster_carousel.set_single_poster(pix)
            self.media_section.update_movie(media_data)
        else:
            # For TV we need more context usually handled in refresh or update_episode_info
            # but we can do basic refresh here
            series_pix = self._load_pixmap(self._get_translated(media_data, 'poster_path'))
            self.poster_carousel.set_single_poster(series_pix) # Fallback

    def update_episode_info(self, ep_data_list, season_data=None):
        self._current_episode_data = ep_data_list
        self._current_season_data = season_data
        
        # Reload posters for current language
        if self._current_media_data:
            series_pix = self._load_pixmap(self._get_translated(self._current_media_data, 'poster_path'))
            season_pix = self._load_pixmap(self._get_translated(season_data, 'poster_path')) if season_data else None
            
            all_ep_pix = []
            for ed in ep_data_list:
                p_ep = self._load_pixmap(self._get_translated(ed, 'still_path', ed.get('still_path')))
                if p_ep: all_ep_pix.append(p_ep)
            
            self.poster_carousel.set_tv_posters(series_pix, season_pix, *all_ep_pix)
            self.media_section.update_episode(self._current_media_data, ep_data_list)

    def update_tech_info(self, file_data):
        self._current_file_data = file_data
        self.tech_section.update_info(file_data)
        # If no match yet, show unmatched technical view
        if not self._current_media_data:
            self.media_section.update_unmatched(file_data)

    def _on_check_data_clicked(self):
        if not self._current_file_data: return
        dialog = DataSheetDialog(
            file_data=self._current_file_data,
            media_data=self._current_media_data,
            ep_data_list=self._current_episode_data,
            season_data=self._current_season_data,
            children=self._current_children,
            parent=self.window()
        )
        dialog.exec()

    # --- Backward Compatibility Properties ---
    @property
    def poster_label(self):
        return self._PosterCompat(self.poster_carousel)

    @property
    def title_label(self):
        return self.media_section.lbl_main

    class _PosterCompat:
        def __init__(self, carousel): self._carousel = carousel
        def clear(self): self._carousel.clear()
        def setPixmap(self, pixmap): self._carousel.set_single_poster(pixmap)
        def setText(self, text): self._carousel.clear()

    def refresh_style(self):
        """Re-applies styles to all sub-panels."""
        self.setStyleSheet(Theme.get_inspector_style())
        self.data_btn.setStyleSheet(Theme.get_secondary_ghost_button_style())
        if hasattr(self.poster_carousel, 'refresh_style'): self.poster_carousel.refresh_style()
        if hasattr(self.media_section, 'refresh_style'): self.media_section.refresh_style()
        if hasattr(self.tech_section, 'refresh_style'): self.tech_section.refresh_style()

    def set_preferred_language(self, lang):
        self._preferred_language = lang
        self.media_section.set_preferred_language(lang)
        # If we have an active selection, refresh it
        self.refresh()

    def _get_translated(self, data, field, default=""):
        if not data: return default
        details_json = data.get('details_json')
        if details_json:
            try:
                import json
                details = json.loads(details_json)
                if isinstance(details, dict) and self._preferred_language in details:
                    lang_data = details[self._preferred_language]
                    val = lang_data.get(field)
                    if val: return val
            except: pass
        return data.get(field, default)

    def refresh(self):
        if self._current_media_data:
            if self._current_episode_data:
                self.update_episode_info(self._current_episode_data, self._current_season_data)
            else:
                self.update_from_data(self._current_media_data)
        elif self._current_file_data:
            self.update_tech_info(self._current_file_data)
