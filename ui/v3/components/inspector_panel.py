import logging
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton
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
        self.setStyleSheet(f"""
            QFrame#Inspector {{
                background-color: {Theme.SURFACE_DARK};
                border-left: 1px solid {Theme.BORDER};
            }}
        """)
        self._current_file_data = None
        self._current_media_data = None
        self._current_episode_data = None
        self._current_season_data = None
        self._current_children = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 1. Poster Carousel
        self.poster_carousel = PosterCarousel()
        layout.addWidget(self.poster_carousel, alignment=Qt.AlignHCenter)

        # 2. Media Metadata Section
        self.media_section = MediaSection()
        layout.addWidget(self.media_section, 1) # Give it stretch factor

        # 3. Technical Section
        self.tech_section = TechnicalSection()
        layout.addWidget(self.tech_section)

        # 4. Check Data Button
        self.data_btn = QPushButton(T("discovery.inspector.check_data"))
        self.data_btn.setFixedHeight(40)
        self.data_btn.setCursor(Qt.PointingHandCursor)
        self.data_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.SURFACE_LIGHT};
                color: {Theme.TEXT_MAIN};
                border-radius: 8px;
                font-weight: 700;
                border: 1px solid {Theme.BORDER};
            }}
            QPushButton:hover {{ background: {Theme.SURFACE_LIGHTER}; border-color: {Theme.PRIMARY}; }}
        """)
        self.data_btn.clicked.connect(self._on_check_data_clicked)
        layout.addWidget(self.data_btn)

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
        self.media_section.update_status(status)

    def update_from_data(self, media_data):
        self._current_media_data = media_data
        self.media_section.update_media(media_data)

    def update_episode_info(self, ep_data_list, season_data=None):
        self._current_episode_data = ep_data_list
        self._current_season_data = season_data
        self.media_section.update_episode(ep_data_list)

    def update_tech_info(self, file_data):
        self._current_file_data = file_data
        self.tech_section.update_info(file_data)

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
        return self.media_section.title_lbl

    class _PosterCompat:
        def __init__(self, carousel): self._carousel = carousel
        def clear(self): self._carousel.clear()
        def setPixmap(self, pixmap): self._carousel.set_single_poster(pixmap)
        def setText(self, text): self._carousel.clear()
