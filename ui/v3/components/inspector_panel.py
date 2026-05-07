import logging
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QWidget, QScrollArea
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
        self._current_children = []

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

    def update_status(self, status):
        # MediaSection.update_status is now a no-op as logic moved to poster
        self.media_section.update_status(status)

    def update_from_data(self, media_data):
        self._current_media_data = media_data
        # If we have episode info pending, wait for update_episode_info
        if media_data.get('media_type') == 'movie':
            self.media_section.update_movie(media_data)

    def update_episode_info(self, ep_data_list, season_data=None):
        self._current_episode_data = ep_data_list
        self._current_season_data = season_data
        if self._current_media_data:
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
        self.media_section.set_preferred_language(lang)
        # If we have an active selection, refresh it
        self.refresh()

    def refresh(self):
        if self._current_media_data:
            if self._current_episode_data:
                self.update_episode_info(self._current_episode_data, self._current_season_data)
            else:
                self.update_from_data(self._current_media_data)
        elif self._current_file_data:
            self.update_tech_info(self._current_file_data)
