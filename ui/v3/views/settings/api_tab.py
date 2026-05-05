from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab
from core.i18n import T

class APITab(BaseSettingsTab):
    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        header = QLabel(T("settings.api.header"))
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)
        
        layout.addWidget(self._create_section_header(T("settings.api.sections.tmdb")))
        self.tmdb_key_input = self._create_input_group(T("settings.api.fields.tmdb_v3"), self.engine.config.settings.tmdb_key, T("settings.api.fields.tmdb_v3_placeholder"))
        layout.addLayout(self.tmdb_key_input['layout'])
 
        self.tmdb_token_input = self._create_input_group(T("settings.api.fields.tmdb_v4"), self.engine.config.settings.tmdb_bearer_token, T("settings.api.fields.tmdb_v4_placeholder"))
        layout.addLayout(self.tmdb_token_input['layout'])
 
        layout.addSpacing(10)
        layout.addWidget(self._create_section_header(T("settings.api.sections.omdb")))
        self.omdb_key_input = self._create_input_group(T("settings.api.fields.omdb_key"), self.engine.config.settings.omdb_key, T("settings.api.fields.omdb_key_placeholder"))
        layout.addLayout(self.omdb_key_input['layout'])

        layout.addStretch()

    def save_to_settings(self, s):
        s.tmdb_key = self.tmdb_key_input['edit'].text().strip()
        s.tmdb_bearer_token = self.tmdb_token_input['edit'].text().strip()
        s.omdb_key = self.omdb_key_input['edit'].text().strip()
