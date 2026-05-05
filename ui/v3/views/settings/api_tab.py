from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab

class APITab(BaseSettingsTab):
    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        header = QLabel("API Configuration")
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)
        
        layout.addWidget(self._create_section_header("TMDB (THE MOVIE DATABASE)"))
        self.tmdb_key_input = self._create_input_group("TMDB API Key (v3)", self.engine.config.settings.tmdb_key, "Enter your v3 API key")
        layout.addLayout(self.tmdb_key_input['layout'])

        self.tmdb_token_input = self._create_input_group("TMDB Bearer Token (v4)", self.engine.config.settings.tmdb_bearer_token, "Paste your Read Access Token")
        layout.addLayout(self.tmdb_token_input['layout'])

        layout.addSpacing(10)
        layout.addWidget(self._create_section_header("OMDB (FOR IMDB RATINGS)"))
        self.omdb_key_input = self._create_input_group("OMDB API Key", self.engine.config.settings.omdb_key, "Enter your OMDB key")
        layout.addLayout(self.omdb_key_input['layout'])

        layout.addStretch()

    def save_to_settings(self, s):
        s.tmdb_key = self.tmdb_key_input['edit'].text().strip()
        s.tmdb_bearer_token = self.tmdb_token_input['edit'].text().strip()
        s.omdb_key = self.omdb_key_input['edit'].text().strip()
