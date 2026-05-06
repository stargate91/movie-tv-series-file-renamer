from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame
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

        welcome = QLabel(T("settings.api.sections.welcome"))
        welcome.setWordWrap(True)
        welcome.setStyleSheet(f"font-size: 14px; color: {Theme.TEXT_MUTED}; margin-bottom: 5px;")
        layout.addWidget(welcome)

        # Trust Box Container
        trust_frame = QFrame()
        trust_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.SURFACE_LIGHT};
                border: 1px solid {Theme.BORDER};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        trust_layout = QHBoxLayout(trust_frame)
        trust_layout.setContentsMargins(15, 12, 15, 12)
        trust_layout.setSpacing(15)

        lock_icon = QLabel()
        lock_icon.setPixmap(Theme.get_pixmap("lock", size=24, color=Theme.PRIMARY))
        lock_icon.setStyleSheet("border: none; background: transparent;")
        
        trust_text = QLabel(T("settings.api.sections.privacy_note"))
        trust_text.setWordWrap(True)
        trust_text.setStyleSheet(f"color: {Theme.TEXT_MAIN}; font-size: 13px; border: none; background: transparent;")
        
        trust_layout.addWidget(lock_icon)
        trust_layout.addWidget(trust_text, 1)
        
        layout.addWidget(trust_frame)
        layout.addSpacing(10)
        
        layout.addWidget(self._create_section_header(T("settings.api.sections.tmdb")))
        self.tmdb_key_input = self._create_input_group(T("settings.api.fields.tmdb_v3"), self.engine.config.settings.tmdb_key, T("settings.api.fields.tmdb_v3_placeholder"))
        layout.addLayout(self.tmdb_key_input['layout'])
 
        self.tmdb_token_input = self._create_input_group(T("settings.api.fields.tmdb_v4"), self.engine.config.settings.tmdb_bearer_token, T("settings.api.fields.tmdb_v4_placeholder"))
        layout.addLayout(self.tmdb_token_input['layout'])
 
        tmdb_help = self._create_help_text(T("settings.api.fields.tmdb_guide"))
        layout.addWidget(tmdb_help)

        layout.addSpacing(20)
        layout.addWidget(self._create_section_header(T("settings.api.sections.omdb")))
        self.omdb_key_input = self._create_input_group(T("settings.api.fields.omdb_key"), self.engine.config.settings.omdb_key, T("settings.api.fields.omdb_key_placeholder"))
        layout.addLayout(self.omdb_key_input['layout'])

        omdb_help = self._create_help_text(T("settings.api.fields.omdb_guide"))
        layout.addWidget(omdb_help)

        layout.addStretch()

    def save_to_settings(self, s):
        s.tmdb_key = self.tmdb_key_input['edit'].text().strip()
        s.tmdb_bearer_token = self.tmdb_token_input['edit'].text().strip()
        s.omdb_key = self.omdb_key_input['edit'].text().strip()

    def _create_help_text(self, text):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setOpenExternalLinks(True)
        lbl.setStyleSheet(Theme.get_card_description_style() + "margin-top: 5px;")
        return lbl
