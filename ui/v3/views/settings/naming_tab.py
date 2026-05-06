from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QFrame
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab
from core.i18n import T

class NamingTab(BaseSettingsTab):
    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QLabel(T("settings.naming.header"))
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)

        # --- Section: Global Styles ---
        layout.addWidget(self._create_section_header(T("settings.naming.sections.styling")))
        style_row = QHBoxLayout()
        
        # Casing
        c_group = QVBoxLayout()
        c_group.addWidget(QLabel(T("settings.naming.fields.casing")))
        self.casing_combo = QComboBox()
        self.casing_combo.setFixedWidth(160)
        c_opts = [
            (T("settings.naming.casing_options.none"), "none"), 
            (T("settings.naming.casing_options.lower"), "lower"), 
            (T("settings.naming.casing_options.upper"), "upper"), 
            (T("settings.naming.casing_options.title"), "title")
        ]
        for label, val in c_opts:
            self.casing_combo.addItem(label, val)
        idx = self.casing_combo.findData(self.engine.config.settings.filename_case)
        if idx >= 0: self.casing_combo.setCurrentIndex(idx)
        c_group.addWidget(self.casing_combo)
        style_row.addLayout(c_group)
        
        # Separator
        s_group = QVBoxLayout()
        s_group.addWidget(QLabel(T("settings.naming.fields.separator")))
        self.sep_combo = QComboBox()
        self.sep_combo.setFixedWidth(160)
        s_opts = [
            (T("settings.naming.separator_options.space"), "space"), 
            (T("settings.naming.separator_options.dot"), "dot"), 
            (T("settings.naming.separator_options.dash"), "dash"), 
            (T("settings.naming.separator_options.underscore"), "underscore")
        ]
        for label, val in s_opts:
            self.sep_combo.addItem(label, val)
        idx = self.sep_combo.findData(self.engine.config.settings.separator)
        if idx >= 0: self.sep_combo.setCurrentIndex(idx)
        s_group.addWidget(self.sep_combo)
        style_row.addLayout(s_group)
        style_row.addStretch()
        layout.addLayout(style_row)

        layout.addWidget(Theme.create_hline())

        # --- Section: Movie Template ---
        layout.addWidget(self._create_section_header(T("settings.naming.sections.movie")))
        self.movie_tpl = self._create_input_group(T("settings.naming.fields.movie_tpl"), self.engine.config.settings.movie_template, "{Title} ({Year})")
        layout.addLayout(self.movie_tpl['layout'])
        
        m_tags = ["Title", "Year", "Resolution", "VideoCodec", "Part", "PartRaw", "HDR", "OriginalTitle", "IMDB_ID"]
        layout.addLayout(self._create_tag_chips(m_tags, self.movie_tpl['edit']))

        layout.addSpacing(10)

        # --- Section: Episode Template ---
        layout.addWidget(self._create_section_header(T("settings.naming.sections.episode")))
        self.episode_tpl = self._create_input_group(T("settings.naming.fields.episode_tpl"), self.engine.config.settings.episode_template, "{ShowTitle} - {Season}{Episode} - {EpisodeTitle}")
        layout.addLayout(self.episode_tpl['layout'])
        
        e_tags = ["ShowTitle", "Season", "Episode", "Part", "Network", "EpisodeTitle", "Year", "Resolution", "VideoCodec"]
        layout.addLayout(self._create_tag_chips(e_tags, self.episode_tpl['edit']))

        # --- Section: Multi-Part Formatting ---
        layout.addWidget(self._create_section_header(T("settings.naming.sections.multi_part") or "Multi-Part Formatting"))
        part_row = QHBoxLayout()
        
        # Keyword
        p_kw_group = QVBoxLayout()
        p_kw_group.addWidget(QLabel(T("settings.naming.fields.part_keyword") or "Keyword"))
        self.part_keyword_combo = QComboBox()
        self.part_keyword_combo.setFixedWidth(120)
        for kw in ["Part", "CD", "Disc", "Disk", "None"]:
            self.part_keyword_combo.addItem(kw, kw)
        idx = self.part_keyword_combo.findData(self.engine.config.settings.multi_part_keyword)
        if idx >= 0: self.part_keyword_combo.setCurrentIndex(idx)
        p_kw_group.addWidget(self.part_keyword_combo)
        part_row.addLayout(p_kw_group)
        
        # Style
        p_st_group = QVBoxLayout()
        p_st_group.addWidget(QLabel(T("settings.naming.fields.part_style") or "Numbering Style"))
        self.part_style_combo = QComboBox()
        self.part_style_combo.setFixedWidth(160)
        st_opts = [
            ("1, 2, 3...", "number"),
            ("01, 02, 03...", "zero_padded"),
            ("I, II, III...", "roman"),
            ("A, B, C...", "letter")
        ]
        for label, val in st_opts:
            self.part_style_combo.addItem(label, val)
        idx = self.part_style_combo.findData(self.engine.config.settings.multi_part_style)
        if idx >= 0: self.part_style_combo.setCurrentIndex(idx)
        p_st_group.addWidget(self.part_style_combo)
        part_row.addLayout(p_st_group)
        
        # Internal Separator
        p_sep_group = QVBoxLayout()
        p_sep_group.addWidget(QLabel(T("settings.naming.fields.part_separator") or "Inner Separator"))
        self.part_sep_combo = QComboBox()
        self.part_sep_combo.setFixedWidth(140)
        sep_opts = [
            (T("settings.naming.separator_options.space"), "space"),
            (T("settings.naming.separator_options.none"), "none"),
            (T("settings.naming.separator_options.dot"), "dot"),
            (T("settings.naming.separator_options.dash"), "dash"),
            (T("settings.naming.separator_options.underscore"), "underscore")
        ]
        for label, val in sep_opts:
            self.part_sep_combo.addItem(label, val)
        idx = self.part_sep_combo.findData(self.engine.config.settings.multi_part_separator)
        if idx >= 0: self.part_sep_combo.setCurrentIndex(idx)
        p_sep_group.addWidget(self.part_sep_combo)
        part_row.addLayout(p_sep_group)
        
        part_row.addStretch()
        layout.addLayout(part_row)

        layout.addSpacing(20)
        layout.addWidget(self._create_section_header(T("settings.naming.sections.custom")))
        self.custom_var_input = self._create_input_group(T("settings.naming.fields.custom_val"), self.engine.config.settings.custom_variable, T("settings.naming.fields.custom_placeholder"))
        layout.addLayout(self.custom_var_input['layout'])

        layout.addStretch()

    def save_to_settings(self, s):
        s.filename_case = self.casing_combo.currentData()
        s.separator = self.sep_combo.currentData()
        s.movie_template = self.movie_tpl['edit'].text()
        s.episode_template = self.episode_tpl['edit'].text()
        s.multi_part_keyword = self.part_keyword_combo.currentData()
        s.multi_part_style = self.part_style_combo.currentData()
        s.multi_part_separator = self.part_sep_combo.currentData()
        s.custom_variable = self.custom_var_input['edit'].text()
