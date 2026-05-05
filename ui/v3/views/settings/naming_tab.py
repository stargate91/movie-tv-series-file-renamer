from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QFrame
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab

class NamingTab(BaseSettingsTab):
    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QLabel("Naming Templates & Styles")
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)

        # --- Section: Global Styles ---
        layout.addWidget(self._create_section_header("GLOBAL FILENAME STYLING"))
        style_row = QHBoxLayout()
        
        # Casing
        c_group = QVBoxLayout()
        c_group.addWidget(QLabel("Filename Casing"))
        self.casing_combo = QComboBox()
        self.casing_combo.setFixedWidth(160)
        for label, val in [("Original", "none"), ("lower case", "lower"), ("UPPER CASE", "upper"), ("Title Case", "title")]:
            self.casing_combo.addItem(label, val)
        idx = self.casing_combo.findData(self.engine.config.settings.filename_case)
        if idx >= 0: self.casing_combo.setCurrentIndex(idx)
        c_group.addWidget(self.casing_combo)
        style_row.addLayout(c_group)
        
        # Separator
        s_group = QVBoxLayout()
        s_group.addWidget(QLabel("Word Separator"))
        self.sep_combo = QComboBox()
        self.sep_combo.setFixedWidth(160)
        for label, val in [("Space", "space"), ("Dot (.)", "dot"), ("Dash (-)", "dash"), ("Underscore (_)", "underscore")]:
            self.sep_combo.addItem(label, val)
        idx = self.sep_combo.findData(self.engine.config.settings.separator)
        if idx >= 0: self.sep_combo.setCurrentIndex(idx)
        s_group.addWidget(self.sep_combo)
        style_row.addLayout(s_group)
        style_row.addStretch()
        layout.addLayout(style_row)

        layout.addWidget(Theme.create_hline())

        # --- Section: Movie Template ---
        layout.addWidget(self._create_section_header("MOVIE NAMING TEMPLATE"))
        self.movie_tpl = self._create_input_group("Movie Template", self.engine.config.settings.movie_template, "{Title} ({Year})")
        layout.addLayout(self.movie_tpl['layout'])
        
        m_tags = ["Title", "Year", "Resolution", "VideoCodec", "AudioCodec", "AudioChannels", "HDR", "OriginalTitle", "IMDB_ID"]
        layout.addLayout(self._create_tag_chips(m_tags, self.movie_tpl['edit']))

        layout.addSpacing(10)

        # --- Section: Episode Template ---
        layout.addWidget(self._create_section_header("TV EPISODE NAMING TEMPLATE"))
        self.episode_tpl = self._create_input_group("Episode Template", self.engine.config.settings.episode_template, "{ShowTitle} - {Season}{Episode} - {EpisodeTitle}")
        layout.addLayout(self.episode_tpl['layout'])
        
        e_tags = ["ShowTitle", "Season", "Episode", "EpisodeTitle", "Year", "Resolution", "VideoCodec", "EpisodeRating"]
        layout.addLayout(self._create_tag_chips(e_tags, self.episode_tpl['edit']))

        layout.addSpacing(20)
        layout.addWidget(self._create_section_header("CUSTOM GLOBAL VARIABLE"))
        self.custom_var_input = self._create_input_group("Custom Tag Value ({Custom})", self.engine.config.settings.custom_variable, "e.g. GroupName")
        layout.addLayout(self.custom_var_input['layout'])

        layout.addStretch()

    def save_to_settings(self, s):
        s.filename_case = self.casing_combo.currentData()
        s.separator = self.sep_combo.currentData()
        s.movie_template = self.movie_tpl['edit'].text()
        s.episode_template = self.episode_tpl['edit'].text()
        s.custom_variable = self.custom_var_input['edit'].text()
