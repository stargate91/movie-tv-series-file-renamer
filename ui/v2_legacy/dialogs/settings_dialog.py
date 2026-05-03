from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QCheckBox, QComboBox, QFormLayout, QTabWidget, QWidget, QMenu, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

class SettingsDialog(QDialog):
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.cfg = config_manager
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 450)
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # --- API Tab ---
        api_tab = QWidget()
        api_layout = QFormLayout(api_tab)
        self.omdb_input = QLineEdit(self.cfg.settings.omdb_key)
        self.tmdb_input = QLineEdit(self.cfg.settings.tmdb_key)
        self.tmdb_token = QLineEdit(self.cfg.settings.tmdb_bearer_token)
        
        api_layout.addRow("OMDB API Key:", self.omdb_input)
        api_layout.addRow("TMDB API Key:", self.tmdb_input)
        api_layout.addRow("TMDB Bearer Token:", self.tmdb_token)
        self.tabs.addTab(api_tab, "API Keys")

        # --- Language Tab ---
        lang_tab = QWidget()
        lang_layout = QFormLayout(lang_tab)
        
        languages = [
            ("Hungarian", "hu-HU"), ("English", "en-US"), ("German", "de-DE"),
            ("Spanish", "es-ES"), ("French", "fr-FR"), ("Italian", "it-IT"),
            ("Portuguese (Brazil)", "pt-BR"), ("Polish", "pl-PL"), ("Russian", "ru-RU")
        ]
        
        self.lang_combo = QComboBox()
        for name, code in languages:
            self.lang_combo.addItem(name, code)
        self.s = self.cfg.settings
        idx = self.lang_combo.findData(self.s.metadata_language)
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        
        self.fallback_combo = QComboBox()
        self.fallback_combo.addItem("None (API Default)", "none")
        for name, code in languages:
            self.fallback_combo.addItem(name, code)
        val = self.s.fallback_language or "none"
        idx = self.fallback_combo.findData(val)
        if idx >= 0: self.fallback_combo.setCurrentIndex(idx)
        
        lang_layout.addRow("Primary Language:", self.lang_combo)
        lang_layout.addRow("Fallback Language:", self.fallback_combo)
        self.tabs.addTab(lang_tab, "Localization")

        # --- Format Tab ---
        format_tab = QWidget()
        format_layout = QFormLayout(format_tab)
        
        self.case_combo = QComboBox()
        self.case_combo.addItems(["none", "lower", "upper", "title"])
        self.case_combo.setCurrentText(self.cfg.settings.filename_case)
        
        self.sep_combo = QComboBox()
        self.sep_combo.addItems(["space", "dot", "dash", "underscore"])
        self.sep_combo.setCurrentText(self.cfg.settings.separator)
        
        self.padding_check = QCheckBox("Use Zero Padding (S01E01)")
        self.padding_check.setChecked(self.cfg.settings.zero_padding)
        
        format_layout.addRow("Filename Case:", self.case_combo)
        format_layout.addRow("Separator:", self.sep_combo)
        format_layout.addRow(self.padding_check)
        self.tabs.addTab(format_tab, "Formatting")

        # --- Filters Tab ---
        filters_tab = QWidget()
        filters_layout = QFormLayout(filters_tab)
        
        self.ext_input = QLineEdit(self.cfg.settings.video_extensions)
        self.ext_input.setPlaceholderText(".mp4, .mkv, .avi ...")
        
        from PySide6.QtWidgets import QSpinBox
        self.size_input = QSpinBox()
        self.size_input.setRange(0, 50000)
        self.size_input.setSuffix(" MB")
        self.size_input.setValue(self.cfg.settings.vid_size)
        
        filters_layout.addRow("Video Extensions:", self.ext_input)
        filters_layout.addRow("Min. File Size:", self.size_input)
        
        help_lbl = QLabel("Note: Separate extensions with commas. Files smaller than the min size will be ignored.")
        help_lbl.setStyleSheet("color: #6b7280; font-size: 11px; margin-top: 10px;")
        help_lbl.setWordWrap(True)
        filters_layout.addRow(help_lbl)
        
        self.tabs.addTab(filters_tab, "Filters")
        
        # --- Renaming Tab ---
        rename_tab = QWidget()
        rename_layout = QFormLayout(rename_tab)
        
        self.movie_tmpl = QLineEdit(self.cfg.settings.movie_template)
        self.tv_tmpl = QLineEdit(self.cfg.settings.episode_template)
        self.custom_input = QLineEdit(self.cfg.settings.custom_variable)
        
        rename_layout.addRow("Movie Template:", self.movie_tmpl)
        rename_layout.addRow("TV Template:", self.tv_tmpl)
        rename_layout.addRow("Custom Variable:", self.custom_input)
        
        # Legend / Variable Picker (Minimalist)
        legend_container = QWidget()
        legend_container.setStyleSheet("""
            QWidget { background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }
            QLabel { color: #6b7280; font-size: 10px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; border: none; background: transparent; }
            QPushButton { 
                background-color: white; color: #374151; border: 1px solid #d1d5db; 
                padding: 4px 8px; border-radius: 4px; font-size: 11px; font-family: 'Consolas', monospace;
            }
            QPushButton:hover { background-color: #f3f4f6; border-color: #9ca3af; }
        """)
        legend_layout = QVBoxLayout(legend_container)
        legend_layout.setSpacing(10)
        
        # Helper to create chip layouts
        def create_chip_layout(vars_list, target_input=None):
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0,0,0,0)
            layout.setSpacing(6)
            for var in vars_list:
                btn = QPushButton(f"{{{var}}}")
                btn.setCursor(Qt.PointingHandCursor)
                if target_input:
                    btn.clicked.connect(lambda checked=False, v=var, t=target_input: self.insert_var(f"{{{v}}}", t))
                else:
                    btn.clicked.connect(lambda checked=False, v=var: self.show_var_menu(f"{{{v}}}"))
                layout.addWidget(btn)
            layout.addStretch()
            return container

        # Movie Section
        legend_layout.addWidget(QLabel("Movie Metadata (Inserts into Movie Template)"))
        movie_meta_vars = [
            "movie_title", "movie_release_date", "movie_year", "genres", 
            "imdb_rating", "rotten_rating", "metacritic_rating"
        ]
        legend_layout.addWidget(create_chip_layout(movie_meta_vars, self.movie_tmpl))
        
        # Release Info (Common)
        legend_layout.addWidget(QLabel("Release & Source Info (Shared)"))
        release_vars = ["release_group", "source", "edition", "streaming_service", "other"]
        legend_layout.addWidget(create_chip_layout(release_vars)) # Still uses menu as it's shared
        
        # TV Section
        legend_layout.addWidget(QLabel("TV Metadata (Inserts into TV Template)"))
        tv_meta_vars = [
            "series_title", "episode_title", "season_number", "episode_number", 
            "air_date", "air_year", "status", "genres", "imdb_rating", 
            "first_air_year", "last_air_year"
        ]
        legend_layout.addWidget(create_chip_layout(tv_meta_vars, self.tv_tmpl))

        # Technical Section (Shared)
        legend_layout.addWidget(QLabel("Technical Details (Shared)"))
        tech_video = ["resolution", "video_codec", "video_bitrate", "framerate", "hdr_type", "bit_depth"]
        legend_layout.addWidget(create_chip_layout(tech_video))
        
        legend_layout.addWidget(create_chip_layout(["audio_codec", "audio_channels", "first_audio_channel_language", "audio_channels_description", "audio_streams_count", "subtitle_languages"]))
        
        legend_layout.addWidget(QLabel("Other"))
        legend_layout.addWidget(create_chip_layout(["custom_variable"]))

        rename_layout.addRow(legend_container)
        
        self.tabs.addTab(rename_tab, "Templates")
        
        # --- Extras Tab ---
        extras_tab = QWidget()
        extras_v_layout = QVBoxLayout(extras_tab)
        extras_form = QFormLayout()
        
        self.extra_action_combo = QComboBox()
        self.extra_action_combo.addItems(["skip", "delete", "rename"])
        self.extra_action_combo.setCurrentText(self.cfg.settings.extra_action)
        
        self.movie_extra_tmpl = QLineEdit(self.cfg.settings.movie_extra_template)
        self.episode_extra_tmpl = QLineEdit(self.cfg.settings.episode_extra_template)
        
        extras_form.addRow("Action for Extras:", self.extra_action_combo)
        extras_form.addRow("Movie Extra Template:", self.movie_extra_tmpl)
        extras_form.addRow("TV Extra Template:", self.episode_extra_tmpl)
        
        extras_v_layout.addLayout(extras_form)

        # Legend for Extras
        extra_legend = QWidget()
        extra_legend.setStyleSheet(legend_container.styleSheet())
        extra_leg_layout = QVBoxLayout(extra_legend)
        
        extra_leg_layout.addWidget(QLabel("Extra-Specific Variables"))
        extra_leg_layout.addWidget(create_chip_layout(["extra_type", "original"]))
        
        extra_leg_layout.addWidget(QLabel("Inherited from Movie Parent"))
        extra_leg_layout.addWidget(create_chip_layout(["movie_title", "movie_year", "genres"], self.movie_extra_tmpl))
        
        extra_leg_layout.addWidget(QLabel("Inherited from TV Parent"))
        extra_leg_layout.addWidget(create_chip_layout(["series_title", "season_number", "episode_number"], self.episode_extra_tmpl))

        extras_v_layout.addWidget(extra_legend)
        extras_v_layout.addStretch()
        
        self.tabs.addTab(extras_tab, "Extras")
        
        # --- Multi-part Tab ---
        multipart_tab = QWidget()
        multipart_layout = QFormLayout(multipart_tab)
        
        self.mp_pos_combo = QComboBox()
        self.mp_pos_combo.addItems(["prefix", "suffix"])
        self.mp_pos_combo.setCurrentText(self.cfg.settings.multi_part_position)
        
        self.mp_keyword_input = QLineEdit(self.cfg.settings.multi_part_keyword)
        self.mp_keyword_input.setPlaceholderText("CD, Part, Disc, A, B...")
        
        self.mp_style_combo = QComboBox()
        self.mp_style_combo.addItems(["number", "roman", "padded_number", "letter"])
        self.mp_style_combo.setCurrentText(self.cfg.settings.multi_part_style)
        
        self.mp_sep_combo = QComboBox()
        self.mp_sep_combo.addItems(["space", "dot", "dash", "underscore", "bracket", "none"])
        self.mp_sep_combo.setCurrentText(self.cfg.settings.multi_part_separator)
        
        multipart_layout.addRow("Position:", self.mp_pos_combo)
        multipart_layout.addRow("Keyword:", self.mp_keyword_input)
        multipart_layout.addRow("Numbering Style:", self.mp_style_combo)
        multipart_layout.addRow("Separator:", self.mp_sep_combo)
        
        mp_help = QLabel("Controls how multi-part files (CD1, Part II) are renamed when a naming collision occurs.")
        mp_help.setStyleSheet("color: #6b7280; font-size: 11px; margin-top: 10px;")
        mp_help.setWordWrap(True)
        multipart_layout.addRow(mp_help)
        
        self.tabs.addTab(multipart_tab, "Multi-part")

        # --- Maintenance Tab ---
        maint_tab = QWidget()
        maint_layout = QVBoxLayout(maint_tab)
        maint_layout.setSpacing(15)
        maint_layout.setContentsMargins(30, 30, 30, 30)

        maint_title = QLabel("DATABASE MAINTENANCE")
        maint_title.setStyleSheet("font-weight: bold; color: #374151; font-size: 13px;")
        maint_layout.addWidget(maint_title)

        maint_desc = QLabel("Use these tools to fix issues or reset the application data.")
        maint_desc.setStyleSheet("color: #6b7280; font-size: 11px;")
        maint_desc.setWordWrap(True)
        maint_layout.addWidget(maint_desc)

        maint_layout.addSpacing(10)

        # Clear Cache Button
        cache_btn = QPushButton("🧹 Clear Search & Image Cache")
        cache_btn.setFixedHeight(40)
        cache_btn.setStyleSheet("""
            QPushButton { background-color: #f3f4f6; border: 1px solid #d1d5db; color: #374151; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #e5e7eb; }
        """)
        cache_btn.clicked.connect(self.on_clear_cache_clicked)
        maint_layout.addWidget(cache_btn)

        cache_help = QLabel("Deletes identified metadata and posters. Preserves your API keys and settings.")
        cache_help.setStyleSheet("color: #9ca3af; font-size: 10px;")
        maint_layout.addWidget(cache_help)

        maint_layout.addSpacing(20)

        # Factory Reset Button
        factory_btn = QPushButton("⚠️ FACTORY RESET (Wipe Everything)")
        factory_btn.setFixedHeight(40)
        factory_btn.setStyleSheet("""
            QPushButton { background-color: #fef2f2; border: 1px solid #fecaca; color: #dc2626; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #fee2e2; border-color: #f87171; }
        """)
        factory_btn.clicked.connect(self.on_factory_reset_clicked)
        maint_layout.addWidget(factory_btn)

        factory_help = QLabel("DANGER: This will delete ALL data, including API keys, templates, and history. The app will return to its original state.")
        factory_help.setStyleSheet("color: #ef4444; font-size: 10px;")
        maint_layout.addWidget(factory_help)

        maint_layout.addStretch()
        self.tabs.addTab(maint_tab, "Maintenance")
        
        layout.addWidget(self.tabs)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def save(self):
        self.cfg.settings.omdb_key = self.omdb_input.text()
        self.cfg.settings.tmdb_key = self.tmdb_input.text()
        self.cfg.settings.tmdb_bearer_token = self.tmdb_token.text()
        
        self.cfg.settings.filename_case = self.case_combo.currentText()
        self.cfg.settings.separator = self.sep_combo.currentText()
        self.cfg.settings.zero_padding = self.padding_check.isChecked()
        self.cfg.settings.movie_template = self.movie_tmpl.text()
        self.cfg.settings.episode_template = self.tv_tmpl.text()
        self.cfg.settings.custom_variable = self.custom_input.text()
        
        self.cfg.settings.metadata_language = self.lang_combo.currentData()
        fb = self.fallback_combo.currentData()
        self.cfg.settings.fallback_language = fb if fb != "none" else ""

        # Filters
        self.cfg.settings.video_extensions = self.ext_input.text()
        self.cfg.settings.vid_size = self.size_input.value()

        # Extras
        self.cfg.settings.extra_action = self.extra_action_combo.currentText()
        self.cfg.settings.movie_extra_template = self.movie_extra_tmpl.text()
        self.cfg.settings.episode_extra_template = self.episode_extra_tmpl.text()

        # Multi-part
        self.cfg.settings.multi_part_position = self.mp_pos_combo.currentText()
        self.cfg.settings.multi_part_keyword = self.mp_keyword_input.text()
        self.cfg.settings.multi_part_style = self.mp_style_combo.currentText()
        self.cfg.settings.multi_part_separator = self.mp_sep_combo.currentText()

        self.cfg.save()
        self.accept()

    def show_var_menu(self, var_text):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #d1d5db; border-radius: 4px; padding: 5px; }
            QMenu::item { padding: 5px 20px; color: #374151; }
            QMenu::item:selected { background-color: #f3f4f6; color: #111827; }
        """)
        
        act_movie = menu.addAction(f"Insert into Movie Template")
        act_movie.triggered.connect(lambda: self.insert_var(var_text, self.movie_tmpl))
        
        act_tv = menu.addAction(f"Insert into TV Template")
        act_tv.triggered.connect(lambda: self.insert_var(var_text, self.tv_tmpl))
        
        menu.addSeparator()
        
        act_copy = menu.addAction(f"Copy to Clipboard")
        act_copy.triggered.connect(lambda: QApplication.clipboard().setText(var_text))
        
        menu.exec(QCursor.pos())

    def insert_var(self, var_text, target):
        current_text = target.text()
        cursor_pos = target.cursorPosition()
        new_text = current_text[:cursor_pos] + var_text + current_text[cursor_pos:]
        target.setText(new_text)
        target.setFocus()
        target.setCursorPosition(cursor_pos + len(var_text))

    def on_clear_cache_clicked(self):
        from utils.cache import DataStore
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Clear Cache?", "This will remove all cached metadata and posters. Your settings will be kept. Proceed?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            DataStore.clear_transient_data()
            QMessageBox.information(self, "Done", "Cache cleared successfully.")

    def on_factory_reset_clicked(self):
        from utils.cache import DataStore
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.critical(self, "FACTORY RESET?", "WARNING: This will delete ALL settings, API keys, and cached data.\n\nThis cannot be undone. Are you absolutely sure?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            DataStore.wipe_all_data()
            # Also reset ConfigManager defaults if possible, but wipe_all_data kills the DB settings
            self.cfg.reset_to_defaults() 
            QMessageBox.warning(self, "Reset Complete", "The application has been reset. It is recommended to restart the app now.")
            self.accept()
