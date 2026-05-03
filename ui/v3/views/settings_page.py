from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox, QSpinBox,
                             QPushButton, QLineEdit, QFileDialog, QFrame, QStackedWidget, QListWidget, QListWidgetItem, QMessageBox, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from ui.v3.styles.theme import Theme

class SaveWorker(QThread):
    finished = Signal()
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
    def run(self):
        try: self.engine.config.save()
        except: pass
        self.finished.emit()

class SettingsPage(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.save_worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Left Sidebar for Tabs (Tree for Categories)
        self.tabs_tree = QTreeWidget()
        self.tabs_tree.setFixedWidth(220)
        self.tabs_tree.setHeaderHidden(True)
        self.tabs_tree.setIndentation(0)  # Remove indentation to kill the 'bumszli'
        self.tabs_tree.setRootIsDecorated(False) # No arrows
        self.tabs_tree.setStyleSheet(Theme.get_sidebar_tree_style())
        
        # Add Tabs
        self.general_item = QTreeWidgetItem(self.tabs_tree, ["General"])
        self.styles_item = QTreeWidgetItem(self.tabs_tree, ["Naming Styles"])
        self.naming_item = QTreeWidgetItem(self.tabs_tree, ["File Naming"])
        
        self.folders_root = QTreeWidgetItem(self.tabs_tree, ["Folders"])
        self.folders_org = QTreeWidgetItem(self.folders_root, ["    Organization"])
        self.folders_movies = QTreeWidgetItem(self.folders_root, ["    Movie Folders"])
        self.folders_tv = QTreeWidgetItem(self.folders_root, ["    TV Show Folders"])
        self.folders_root.setExpanded(True)
        self.folders_root.setFlags(self.folders_root.flags() & ~Qt.ItemIsSelectable) # Make category non-selectable?
        
        self.api_item = QTreeWidgetItem(self.tabs_tree, ["API Keys"])
        self.adv_item = QTreeWidgetItem(self.tabs_tree, ["Advanced"])
        
        layout.addWidget(self.tabs_tree)

        # 2. Right Content Area
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {Theme.BACKGROUND};")
        
        # Mapping tree items to stack indices
        self.tab_map = {
            self.general_item: 0,
            self.styles_item: 1,
            self.naming_item: 2,
            self.folders_org: 3,
            self.folders_movies: 4,
            self.folders_tv: 5,
            self.api_item: 6,
            self.adv_item: 7
        }
        
        self.stack.addWidget(self._create_general_tab())          # 0
        self.stack.addWidget(self._create_naming_styles_tab())   # 1
        self.stack.addWidget(self._create_file_naming_tab())     # 2
        self.stack.addWidget(self._create_folder_org_tab())       # 3 (New)
        self.stack.addWidget(self._create_movie_folders_tab())   # 4 (Split)
        self.stack.addWidget(self._create_tv_folders_tab())      # 5 (Split)
        self.stack.addWidget(self._create_api_tab())              # 6
        self.stack.addWidget(self._create_advanced_tab())        # 7
        
        layout.addWidget(self.stack)

        # Connections
        self.tabs_tree.currentItemChanged.connect(self._on_tree_changed)
        self.tabs_tree.setCurrentItem(self.general_item)

    def _on_tree_changed(self, current, previous):
        if current in self.tab_map:
            self.stack.setCurrentIndex(self.tab_map[current])
        elif current.childCount() > 0:
            # If a root item with children is clicked (like Folders), select first child
            self.tabs_tree.setCurrentItem(current.child(0))


    def _create_general_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QLabel("General Settings")
        header.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        layout.addWidget(header)
        layout.addSpacing(10)

        # --- Section: Library ---
        section_lib = QLabel("LIBRARY & SCANNING")
        section_lib.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: 800; font-size: 11px; letter-spacing: 1.5px;")
        layout.addWidget(section_lib)
        
        # Default Scan Directory
        dir_group = QVBoxLayout()
        dir_label = QLabel("Default Scan Directory")
        dir_label.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {Theme.TEXT_MAIN};")
        dir_group.addWidget(dir_label)

        dir_desc = QLabel("This folder will open automatically when you start a new scan.")
        dir_desc.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px;")
        dir_group.addWidget(dir_desc)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setText(self.engine.config.settings.default_scan_path)
        self.path_input.setFixedHeight(45)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.setFixedSize(100, 45)
        browse_btn.clicked.connect(self._on_browse_path)
        
        path_row.addWidget(self.path_input)
        path_row.addWidget(browse_btn)
        dir_group.addLayout(path_row)
        layout.addLayout(dir_group)

        # Min Video Size
        size_group = QHBoxLayout()
        size_label = QLabel("Min. Video Size (MB):")
        size_label.setStyleSheet("font-weight: 600;")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(0, 10000)
        self.size_spin.setValue(self.engine.config.settings.vid_size)
        self.size_spin.setFixedSize(100, 35)
        size_group.addWidget(size_label)
        size_group.addWidget(self.size_spin)
        size_group.addStretch()
        layout.addLayout(size_group)

        layout.addSpacing(10)
        layout.addWidget(Theme.create_hline())

        # --- Section: Metadata ---
        section_meta = QLabel("METADATA & API")
        section_meta.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: 800; font-size: 11px; letter-spacing: 1.5px;")
        layout.addWidget(section_meta)

        self.languages = {
            "hu-HU": "Hungarian (Magyar)",
            "en-US": "English (US)",
            "de-DE": "German (Deutsch)",
            "fr-FR": "French (Français)",
            "es-ES": "Spanish (Español)",
            "it-IT": "Italian (Italiano)"
        }

        # Target Language
        lang_group = QHBoxLayout()
        lang_label = QLabel("Preferred Language:")
        lang_label.setStyleSheet("font-weight: 600;")
        self.lang_combo = QComboBox()
        for code, name in self.languages.items():
            self.lang_combo.addItem(name, code)
        
        # Set current from settings
        idx = self.lang_combo.findData(self.engine.config.settings.metadata_language)
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        
        self.lang_combo.setFixedSize(220, 35)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        
        lang_group.addWidget(lang_label)
        lang_group.addWidget(self.lang_combo)
        lang_group.addStretch()
        layout.addLayout(lang_group)

        # Fallback Language
        fallback_group = QHBoxLayout()
        fallback_label = QLabel("Fallback Language:")
        fallback_label.setStyleSheet("font-weight: 600;")
        self.fallback_combo = QComboBox()
        self.fallback_combo.addItem("None (API Default)", "")
        for code, name in self.languages.items():
            self.fallback_combo.addItem(name, code)

        # Set current from settings
        f_idx = self.fallback_combo.findData(self.engine.config.settings.fallback_language)
        if f_idx >= 0: self.fallback_combo.setCurrentIndex(f_idx)

        self.fallback_combo.setFixedSize(220, 35)
        
        fallback_group.addWidget(fallback_label)
        fallback_group.addWidget(self.fallback_combo)
        fallback_group.addStretch()
        layout.addLayout(fallback_group)

        self._on_lang_changed() # Initial filter

        layout.addSpacing(10)
        layout.addWidget(Theme.create_hline())

        layout.addStretch()
        
        # Save Button
        save_container = QHBoxLayout()
        self.save_btn = QPushButton("Save All Changes")
        self.save_btn.setFixedSize(220, 50)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.PRIMARY}; 
                color: white; 
                font-weight: 800; 
                font-size: 15px;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: {Theme.PRIMARY_HOVER};
            }}
        """)
        self.save_btn.clicked.connect(self._on_save)
        save_container.addWidget(self.save_btn)
        save_container.addStretch()
        layout.addLayout(save_container)

        return widget


    def _create_advanced_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QLabel("Advanced Tools")
        header.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        layout.addWidget(header)
        layout.addWidget(header)
        layout.addSpacing(10)

        # --- Section: Cleanup ---
        layout.addWidget(self._create_section_header("FILE SYSTEM CLEANUP"))
        self.cleanup_cb = QCheckBox("Automatically delete empty folders after renaming")
        self.cleanup_cb.setChecked(self.engine.config.settings.cleanup_empty_folders)
        self.cleanup_cb.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.cleanup_cb)
        
        layout.addSpacing(20)
        layout.addWidget(Theme.create_hline())
        layout.addSpacing(10)

        # --- Section: Danger Zone ---
        section_danger = QLabel("DANGER ZONE")
        section_danger.setStyleSheet(f"color: {Theme.ERROR}; font-weight: 800; font-size: 11px; letter-spacing: 1.5px;")
        layout.addWidget(section_danger)

        danger_card = QFrame()
        # Semi-transparent red background for the card
        danger_card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(239, 68, 68, 0.05); 
                border: 1px solid rgba(239, 68, 68, 0.2); 
                border-radius: 12px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        danger_layout = QVBoxLayout(danger_card)
        danger_layout.setContentsMargins(25, 25, 25, 25)
        danger_layout.setSpacing(15)
        
        wipe_title = QLabel("Wipe Library Data")
        wipe_title.setStyleSheet(f"font-weight: 700; font-size: 18px; color: {Theme.ERROR};")
        danger_layout.addWidget(wipe_title)
        
        wipe_desc = QLabel("This will delete all indexed files, API results, posters, and history.\nYour settings (API keys, paths, formats) will be preserved.")
        wipe_desc.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 14px; line-height: 1.4;")
        danger_layout.addWidget(wipe_desc)
        
        danger_layout.addSpacing(10)
        
        btn_container = QHBoxLayout()
        self.wipe_btn = QPushButton("Wipe Everything (Except Settings)")
        self.wipe_btn.setFixedWidth(320)
        self.wipe_btn.setCursor(Qt.PointingHandCursor)
        self.wipe_btn.setStyleSheet(Theme.get_danger_button_style())
        self.wipe_btn.clicked.connect(self._on_wipe_database)
        btn_container.addWidget(self.wipe_btn)
        btn_container.addStretch()
        
        danger_layout.addLayout(btn_container)
        
        layout.addWidget(danger_card)
        layout.addStretch()
        return widget

    def _on_wipe_database(self):
        reply = QMessageBox.critical(
            self, "Confirm Wipe", 
            "Are you absolutely sure?\n\nThis will permanently delete all library data, including manual matches and history.\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.engine.db.clear_all()
            QMessageBox.information(self, "Wiped", "All library data has been cleared.")
            # Trigger a refresh on discovery page if it exists
            # (In a real app we'd use a signal, but for now we just clear the DB)

    def _create_file_naming_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        header = QLabel("File Naming Settings")
        header.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        layout.addWidget(header)
        
        # --- Custom Tag Value ---
        self.custom_var_input = self._create_input_group("Custom Tag Value", self.engine.config.settings.custom_variable, "e.g. BluRay-GROUPNAME")
        layout.addLayout(self.custom_var_input['layout'])
        layout.addSpacing(10)
        
        # --- Movie Naming ---
        layout.addWidget(self._create_section_header("MOVIE NAMING"))
        
        basic_movie_tags = ["Title", "Year", "Resolution"]
        adv_movie_tags = ["OriginalTitle", "ReleaseDate", "RatingImdb", "Director", "VideoCodec", "VideoBitrate", "Framerate", "BitDepth", "HDR", "AudioCodec", "AudioChannels", "Custom", "TMDB_ID", "IMDB_ID"]
        
        self.movie_tpl = self._create_input_group("Movie Name Template", self.engine.config.settings.movie_template, "{Title} ({Year}) - {Resolution}")
        layout.addLayout(self.movie_tpl['layout'])
        
        # Basic Chips
        layout.addLayout(self._create_tag_chips(basic_movie_tags, self.movie_tpl['edit']))
        
        # Advanced Toggle
        self.adv_movie_container = QWidget()
        adv_layout = QVBoxLayout(self.adv_movie_container)
        adv_layout.setContentsMargins(0, 0, 0, 0)
        adv_layout.addLayout(self._create_tag_chips(adv_movie_tags, self.movie_tpl['edit']))
        self.adv_movie_container.setVisible(False)
        
        toggle_btn = QPushButton("Show Advanced Tags")
        toggle_btn.setCheckable(True)
        toggle_btn.setFixedWidth(150)
        toggle_btn.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; text-decoration: underline; border: none; background: transparent; text-align: left;")
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.toggled.connect(lambda checked: self.adv_movie_container.setVisible(checked))
        toggle_btn.toggled.connect(lambda checked: toggle_btn.setText("Hide Advanced Tags" if checked else "Show Advanced Tags"))
        
        layout.addWidget(toggle_btn)
        layout.addWidget(self.adv_movie_container)

        layout.addSpacing(15)
        layout.addWidget(Theme.create_hline())
        layout.addSpacing(10)
        
        # --- TV Naming ---
        layout.addWidget(self._create_section_header("TV SHOW NAMING"))
        
        basic_tv_tags = ["ShowTitle", "EpisodeTitle", "Resolution", "Season", "Episode", "EpisodeAirDate", "EpisodeAirYear"]
        adv_tv_tags = ["OriginalTitle", "Director", "VideoCodec", "VideoBitrate", "Framerate", "BitDepth", "HDR", "AudioCodec", "AudioChannels", "Custom", "EpisodeRatingImdb", "EpisodeTMDB_ID", "EpisodeIMDB_ID"]
        
        self.episode_tpl = self._create_input_group("Episode Name Template", self.engine.config.settings.episode_template, "{ShowTitle} - S{Season}E{Episode} - {EpisodeTitle}")
        layout.addLayout(self.episode_tpl['layout'])
        
        # Basic Chips
        layout.addLayout(self._create_tag_chips(basic_tv_tags, self.episode_tpl['edit']))
        
        # Advanced Toggle
        self.adv_tv_container = QWidget()
        adv_tv_layout = QVBoxLayout(self.adv_tv_container)
        adv_tv_layout.setContentsMargins(0, 0, 0, 0)
        adv_tv_layout.addLayout(self._create_tag_chips(adv_tv_tags, self.episode_tpl['edit']))
        self.adv_tv_container.setVisible(False)
        
        tv_toggle_btn = QPushButton("Show Advanced Tags")
        tv_toggle_btn.setCheckable(True)
        tv_toggle_btn.setFixedWidth(150)
        tv_toggle_btn.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; text-decoration: underline; border: none; background: transparent; text-align: left;")
        tv_toggle_btn.setCursor(Qt.PointingHandCursor)
        tv_toggle_btn.toggled.connect(lambda checked: self.adv_tv_container.setVisible(checked))
        tv_toggle_btn.toggled.connect(lambda checked: tv_toggle_btn.setText("Hide Advanced Tags" if checked else "Show Advanced Tags"))
        
        layout.addWidget(tv_toggle_btn)
        layout.addWidget(self.adv_tv_container)

        layout.addStretch()
        return widget

    def _create_naming_styles_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QLabel("Naming Styles")
        header.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        layout.addWidget(header)
        layout.addSpacing(10)

        # --- Section: Casing ---
        layout.addWidget(self._create_section_header("FILENAME CASING"))
        
        casing_group = QVBoxLayout()
        casing_label = QLabel("Rename Casing")
        casing_label.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {Theme.TEXT_MAIN};")
        casing_group.addWidget(casing_label)

        casing_desc = QLabel("Change the capitalization of the generated file names.")
        casing_desc.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px;")
        casing_group.addWidget(casing_desc)

        self.casing_combo = QComboBox()
        self.casing_combo.addItem("Original (No Change)", "none")
        self.casing_combo.addItem("Title Case (Example Title)", "title")
        self.casing_combo.addItem("UPPER CASE (EXAMPLE TITLE)", "upper")
        self.casing_combo.addItem("lower case (example title)", "lower")
        
        # Set current
        idx = self.casing_combo.findData(self.engine.config.settings.filename_case)
        if idx >= 0: self.casing_combo.setCurrentIndex(idx)
        self.casing_combo.setFixedSize(300, 40)
        casing_group.addWidget(self.casing_combo)
        layout.addLayout(casing_group)

        layout.addSpacing(15)
        layout.addWidget(Theme.create_hline())
        layout.addSpacing(10)

        # --- Section: Separator ---
        layout.addWidget(self._create_section_header("WORD SEPARATOR"))
        
        sep_group = QVBoxLayout()
        sep_label = QLabel("Separator Character")
        sep_label.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {Theme.TEXT_MAIN};")
        sep_group.addWidget(sep_label)

        sep_desc = QLabel("Replace spaces with a custom character (dots, dashes, or underscores).")
        sep_desc.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px;")
        sep_group.addWidget(sep_desc)

        self.sep_combo = QComboBox()
        self.sep_combo.addItem("Space ( )", "space")
        self.sep_combo.addItem("Dot (.)", "dot")
        self.sep_combo.addItem("Dash (-)", "dash")
        self.sep_combo.addItem("Underscore (_)", "underscore")
        
        # Set current
        idx = self.sep_combo.findData(self.engine.config.settings.separator)
        if idx >= 0: self.sep_combo.setCurrentIndex(idx)
        self.sep_combo.setFixedSize(300, 40)
        sep_group.addWidget(self.sep_combo)
        layout.addLayout(sep_group)

        layout.addSpacing(15)
        layout.addWidget(Theme.create_hline())
        layout.addSpacing(10)

        # --- Section: Numbers ---
        layout.addWidget(self._create_section_header("NUMBER FORMATTING"))
        self.zero_pad_cb = QCheckBox("Use Zero Padding (e.g. S01E01 instead of S1E1)")
        self.zero_pad_cb.setChecked(self.engine.config.settings.zero_padding)
        self.zero_pad_cb.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.zero_pad_cb)

        # --- Section: Multi-Part (Collisions) ---
        layout.addWidget(self._create_section_header("MULTI-PART HANDLING"))
        
        multi_desc = QLabel("How to handle files that belong together (e.g. CD1, CD2) when a naming collision occurs.")
        multi_desc.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(multi_desc)

        multi_row1 = QHBoxLayout()
        
        # Keyword
        kw_group = QVBoxLayout()
        kw_group.addWidget(QLabel("Keyword"))
        self.multi_kw_combo = QComboBox()
        self.multi_kw_combo.addItems(["Part", "CD", "Disc", "Disk", "None"])
        idx = self.multi_kw_combo.findText(self.engine.config.settings.multi_part_keyword)
        if idx >= 0: self.multi_kw_combo.setCurrentIndex(idx)
        kw_group.addWidget(self.multi_kw_combo)
        multi_row1.addLayout(kw_group)

        # Style
        style_group = QVBoxLayout()
        style_group.addWidget(QLabel("Number Style"))
        self.multi_style_combo = QComboBox()
        self.multi_style_combo.addItem("1, 2, 3", "number")
        self.multi_style_combo.addItem("01, 02, 03", "zero_padded")
        self.multi_style_combo.addItem("I, II, III", "roman")
        self.multi_style_combo.addItem("A, B, C", "letter")
        idx = self.multi_style_combo.findData(self.engine.config.settings.multi_part_style)
        if idx >= 0: self.multi_style_combo.setCurrentIndex(idx)
        style_group.addWidget(self.multi_style_combo)
        multi_row1.addLayout(style_group)
        
        layout.addLayout(multi_row1)

        multi_row2 = QHBoxLayout()

        # Position
        pos_group = QVBoxLayout()
        pos_group.addWidget(QLabel("Position"))
        self.multi_pos_combo = QComboBox()
        self.multi_pos_combo.addItem("Suffix (at end)", "suffix")
        self.multi_pos_combo.addItem("Prefix (at start)", "prefix")
        idx = self.multi_pos_combo.findData(self.engine.config.settings.multi_part_position)
        if idx >= 0: self.multi_pos_combo.setCurrentIndex(idx)
        pos_group.addWidget(self.multi_pos_combo)
        multi_row2.addLayout(pos_group)

        # Separator
        msep_group = QVBoxLayout()
        msep_group.addWidget(QLabel("Part Separator"))
        self.multi_sep_combo = QComboBox()
        self.multi_sep_combo.addItem("Space ( )", "space")
        self.multi_sep_combo.addItem("Dot (.)", "dot")
        self.multi_sep_combo.addItem("Dash (-)", "dash")
        self.multi_sep_combo.addItem("Underscore (_)", "underscore")
        self.multi_sep_combo.addItem("None", "none")
        idx = self.multi_sep_combo.findData(self.engine.config.settings.multi_part_separator)
        if idx >= 0: self.multi_sep_combo.setCurrentIndex(idx)
        msep_group.addWidget(self.multi_sep_combo)
        multi_row2.addLayout(msep_group)

        layout.addLayout(multi_row2)

        layout.addStretch()
        return widget

    def _create_folder_org_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QLabel("Folder Organization")
        header.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        layout.addWidget(header)
        layout.addSpacing(10)

        # --- Section: Global Move ---
        layout.addWidget(self._create_section_header("FILE MOVEMENT"))
        
        self.move_files_cb = QCheckBox("Enable file moving / copying to target folders")
        self.move_files_cb.setChecked(self.engine.config.settings.move_files)
        self.move_files_cb.setStyleSheet("font-weight: 700; font-size: 14px;")
        layout.addWidget(self.move_files_cb)
        
        move_desc = QLabel("If disabled, files will be renamed in their original location.")
        move_desc.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px; margin-left: 30px;")
        layout.addWidget(move_desc)

        layout.addSpacing(15)
        layout.addWidget(Theme.create_hline())
        layout.addSpacing(10)

        # --- Section: Target Root ---
        layout.addWidget(self._create_section_header("ROOT TARGET DIRECTORY"))
        
        self.base_path_input = self._create_path_input("Master Target Folder", self.engine.config.settings.base_target_path, 'root')
        self.base_path_input['edit'].setEnabled(self.move_files_cb.isChecked())
        layout.addLayout(self.base_path_input['layout'])

        self.auto_org_cb = QCheckBox("Automatically create 'Movies' and 'TV Shows' subfolders")
        self.auto_org_cb.setChecked(self.engine.config.settings.auto_organize_by_type)
        self.auto_org_cb.setEnabled(self.move_files_cb.isChecked())
        layout.addWidget(self.auto_org_cb)

        # Inline subfolder names
        subfolder_row = QHBoxLayout()
        subfolder_row.setContentsMargins(30, 0, 0, 0)
        
        self.movie_sub_name = self._create_input_group("Movies Folder Name", self.engine.config.settings.movies_subfolder_name, "Movies")
        self.movie_sub_name['edit'].setEnabled(self.move_files_cb.isChecked() and self.auto_org_cb.isChecked())
        subfolder_row.addLayout(self.movie_sub_name['layout'])

        self.show_sub_name = self._create_input_group("TV Shows Folder Name", self.engine.config.settings.shows_subfolder_name, "TV Shows")
        self.show_sub_name['edit'].setEnabled(self.move_files_cb.isChecked() and self.auto_org_cb.isChecked())
        subfolder_row.addLayout(self.show_sub_name['layout'])
        
        layout.addLayout(subfolder_row)

        # Connections
        self.move_files_cb.toggled.connect(self._update_org_states)
        self.auto_org_cb.toggled.connect(self._update_org_states)
        
        # Initial State Update
        self._update_org_states()

        layout.addStretch()
        return widget

    def _update_org_states(self):
        """Dynamicly enable/disable folder organization inputs based on check states."""
        can_move = self.move_files_cb.isChecked()
        auto_org = self.auto_org_cb.isChecked()
        
        self.base_path_input['edit'].setEnabled(can_move)
        self.auto_org_cb.setEnabled(can_move)
        
        self.movie_sub_name['edit'].setEnabled(can_move and auto_org)
        self.show_sub_name['edit'].setEnabled(can_move and auto_org)

    def _create_movie_folders_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        header = QLabel("Movie Folder Structure")
        header.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        layout.addWidget(header)

        layout.addWidget(self._create_section_header("DIRECTORY OVERRIDE"))
        self.movie_target_input = self._create_path_input("Custom Movie Directory", self.engine.config.settings.target_dir_movies, 'movie')
        layout.addLayout(self.movie_target_input['layout'])
        
        hint = QLabel("💡 If empty, the Master Target Folder will be used.")
        hint.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-size: 11px; font-style: italic;")
        layout.addWidget(hint)

        layout.addSpacing(15)
        layout.addWidget(Theme.create_hline())
        layout.addSpacing(10)

        layout.addWidget(self._create_section_header("MOVIE FOLDERS"))
        self.movie_folder_cb = QCheckBox("Organize each Movie into its own subfolder")
        self.movie_folder_cb.setChecked(self.engine.config.settings.create_movie_folder)
        self.movie_folder_cb.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.movie_folder_cb)
        
        self.movie_folder_tpl = self._create_input_group("Folder Name Template", self.engine.config.settings.movie_folder_template, "{Title} ({Year})")
        self.movie_folder_tpl['edit'].setEnabled(self.movie_folder_cb.isChecked())
        self.movie_folder_cb.toggled.connect(self.movie_folder_tpl['edit'].setEnabled)
        layout.addLayout(self.movie_folder_tpl['layout'])
        
        # Tags - Basic
        layout.addLayout(self._create_tag_chips(["Title", "Year", "Resolution"], self.movie_folder_tpl['edit']))
        
        # Tags - Advanced Toggle
        adv_tags = ["ReleaseDate", "IMDbRating", "Director", "OriginalTitle", "VideoCodec", "VideoBitrate", 
                    "Framerate", "BitDepth", "HDRType", "AudioCodec", "AudioChannels", "Custom"]
        
        self.adv_movie_folder_container = QWidget()
        adv_mf_layout = QVBoxLayout(self.adv_movie_folder_container)
        adv_mf_layout.setContentsMargins(0, 0, 0, 0)
        adv_mf_layout.addLayout(self._create_tag_chips(adv_tags, self.movie_folder_tpl['edit']))
        self.adv_movie_folder_container.setVisible(False)
        
        mf_toggle_btn = QPushButton("Show Advanced Tags")
        mf_toggle_btn.setCheckable(True)
        mf_toggle_btn.setFixedWidth(150)
        mf_toggle_btn.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; text-decoration: underline; border: none; background: transparent; text-align: left;")
        mf_toggle_btn.setCursor(Qt.PointingHandCursor)
        mf_toggle_btn.toggled.connect(lambda checked: self.adv_movie_folder_container.setVisible(checked))
        mf_toggle_btn.toggled.connect(lambda checked: mf_toggle_btn.setText("Hide Advanced Tags" if checked else "Show Advanced Tags"))
        
        layout.addWidget(mf_toggle_btn)
        layout.addWidget(self.adv_movie_folder_container)

        layout.addStretch()
        return widget

    def _create_tv_folders_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        header = QLabel("TV Show Folder Structure")
        header.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        layout.addWidget(header)

        layout.addWidget(self._create_section_header("DIRECTORY OVERRIDE"))
        self.show_target_input_item = self._create_path_input("Custom TV Show Directory", self.engine.config.settings.target_dir_shows, 'show')
        self.show_target_input = self.show_target_input_item['edit']
        layout.addLayout(self.show_target_input_item['layout'])
        
        hint = QLabel("💡 If empty, the Master Target Folder will be used.")
        hint.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-size: 11px; font-style: italic;")
        layout.addWidget(hint)

        layout.addSpacing(15)
        layout.addWidget(Theme.create_hline())
        layout.addSpacing(10)

        layout.addWidget(self._create_section_header("TV SHOWS ORGANIZATION"))
        self.show_folder_cb = QCheckBox("Create Folder for TV Shows")
        self.show_folder_cb.setChecked(self.engine.config.settings.create_show_folder)
        self.show_folder_cb.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.show_folder_cb)

        self.show_folder_tpl = self._create_input_group("Show Folder Template", self.engine.config.settings.show_folder_template, "{ShowTitle}")
        self.show_folder_tpl['edit'].setEnabled(self.show_folder_cb.isChecked())
        self.show_folder_cb.toggled.connect(self.show_folder_tpl['edit'].setEnabled)
        layout.addLayout(self.show_folder_tpl['layout'])
        
        # Tags - Basic
        basic_show_tags = ["SeriesTitle", "FirstAirDate", "LastAirDate", "FirstAirYear", "LastAirYear", "YearRange", "Status"]
        layout.addLayout(self._create_tag_chips(basic_show_tags, self.show_folder_tpl['edit']))
        
        # Tags - Advanced Toggle
        adv_show_tags = ["Director", "SeriesRating", "OriginalTitle", "Type", "Resolution", "EpisodeCount", "SeasonCount"]
        
        self.adv_show_folder_container = QWidget()
        adv_sf_layout = QVBoxLayout(self.adv_show_folder_container)
        adv_sf_layout.setContentsMargins(0, 0, 0, 0)
        adv_sf_layout.addLayout(self._create_tag_chips(adv_show_tags, self.show_folder_tpl['edit']))
        self.adv_show_folder_container.setVisible(False)
        
        sf_toggle_btn = QPushButton("Show Advanced Tags")
        sf_toggle_btn.setCheckable(True)
        sf_toggle_btn.setFixedWidth(150)
        sf_toggle_btn.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; text-decoration: underline; border: none; background: transparent; text-align: left;")
        sf_toggle_btn.setCursor(Qt.PointingHandCursor)
        sf_toggle_btn.toggled.connect(lambda checked: self.adv_show_folder_container.setVisible(checked))
        sf_toggle_btn.toggled.connect(lambda checked: sf_toggle_btn.setText("Hide Advanced Tags" if checked else "Show Advanced Tags"))
        
        layout.addWidget(sf_toggle_btn)
        layout.addWidget(self.adv_show_folder_container)

        self.season_folder_cb = QCheckBox("Create Season Subfolders")
        self.season_folder_cb.setChecked(self.engine.config.settings.create_season_folder)
        self.season_folder_cb.setStyleSheet("margin-left: 20px;")
        layout.addWidget(self.season_folder_cb)
        
        self.season_folder_tpl = self._create_input_group("Season Folder Template", self.engine.config.settings.season_folder_template, "Season {Season}")
        self.season_folder_tpl['edit'].setEnabled(self.season_folder_cb.isChecked())
        self.season_folder_cb.toggled.connect(self.season_folder_tpl['edit'].setEnabled)
        layout.addLayout(self.season_folder_tpl['layout'])
        
        # Season Tags - Basic
        layout.addLayout(self._create_tag_chips(["Season", "SeasonName", "SeasonAirDate", "SeasonAirYear"], self.season_folder_tpl['edit']))
        
        # Season Tags - Advanced Toggle
        self.adv_season_container = QWidget()
        adv_s_layout = QVBoxLayout(self.adv_season_container)
        adv_s_layout.setContentsMargins(0, 0, 0, 0)
        adv_s_layout.addLayout(self._create_tag_chips(["SeasonEpisodeCount", "SeasonResolution"], self.season_folder_tpl['edit']))
        self.adv_season_container.setVisible(False)
        
        s_toggle_btn = QPushButton("Show Advanced Tags")
        s_toggle_btn.setCheckable(True)
        s_toggle_btn.setFixedWidth(150)
        s_toggle_btn.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; text-decoration: underline; border: none; background: transparent; text-align: left;")
        s_toggle_btn.setCursor(Qt.PointingHandCursor)
        s_toggle_btn.toggled.connect(lambda checked: self.adv_season_container.setVisible(checked))
        s_toggle_btn.toggled.connect(lambda checked: s_toggle_btn.setText("Hide Advanced Tags" if checked else "Show Advanced Tags"))
        
        layout.addWidget(s_toggle_btn)
        layout.addWidget(self.adv_season_container)
        
        layout.addSpacing(15)
        layout.addWidget(Theme.create_hline())
        layout.addSpacing(10)

        layout.addWidget(self._create_section_header("EPISODE FOLDERS (OPTIONAL)"))
        self.episode_folder_cb = QCheckBox("Create separate folder for each Episode")
        self.episode_folder_cb.setChecked(self.engine.config.settings.create_episode_folder)
        self.episode_folder_cb.setStyleSheet("margin-left: 20px;")
        layout.addWidget(self.episode_folder_cb)
        
        self.episode_folder_tpl = self._create_input_group("Episode Folder Template", self.engine.config.settings.episode_folder_template, "{EpisodeTitle}")
        self.episode_folder_tpl['edit'].setEnabled(self.episode_folder_cb.isChecked())
        self.episode_folder_cb.toggled.connect(self.episode_folder_tpl['edit'].setEnabled)
        layout.addLayout(self.episode_folder_tpl['layout'])
        
        # Episode Tags - Basic
        basic_ep_tags = ["SeriesTitle", "EpisodeTitle", "Resolution", "Season", "Episode", "EpisodeAirDate", "EpisodeAirYear"]
        layout.addLayout(self._create_tag_chips(basic_ep_tags, self.episode_folder_tpl['edit']))
        
        # Episode Tags - Advanced Toggle
        adv_ep_tags = ["SeriesOriginalTitle", "Director", "VideoCodec", "VideoBitrate", "Framerate", 
                       "BitDepth", "HDRType", "AudioCodec", "AudioChannels", "Custom", "EpisodeRatingImdb"]
        
        self.adv_episode_folder_container = QWidget()
        adv_e_layout = QVBoxLayout(self.adv_episode_folder_container)
        adv_e_layout.setContentsMargins(0, 0, 0, 0)
        adv_e_layout.addLayout(self._create_tag_chips(adv_ep_tags, self.episode_folder_tpl['edit']))
        self.adv_episode_folder_container.setVisible(False)
        
        e_toggle_btn = QPushButton("Show Advanced Tags")
        e_toggle_btn.setCheckable(True)
        e_toggle_btn.setFixedWidth(150)
        e_toggle_btn.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; text-decoration: underline; border: none; background: transparent; text-align: left;")
        e_toggle_btn.setCursor(Qt.PointingHandCursor)
        e_toggle_btn.toggled.connect(lambda checked: self.adv_episode_folder_container.setVisible(checked))
        e_toggle_btn.toggled.connect(lambda checked: e_toggle_btn.setText("Hide Advanced Tags" if checked else "Show Advanced Tags"))
        
        layout.addWidget(e_toggle_btn)
        layout.addWidget(self.adv_episode_folder_container)

        layout.addStretch()
        return widget

    def _create_api_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        header = QLabel("API Configuration")
        header.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {Theme.TEXT_MAIN};")
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
        return widget

    def _create_path_input(self, label_text, value, category):
        group = QVBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {Theme.TEXT_MAIN};")
        group.addWidget(lbl)
        
        row = QHBoxLayout()
        edit = QLineEdit()
        edit.setText(value)
        edit.setReadOnly(True)
        edit.setFixedHeight(40)
        edit.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border: 1px solid {Theme.BORDER}; border-radius: 6px; padding: 0 10px;")
        
        btn = QPushButton("Browse")
        btn.setObjectName("SecondaryButton")
        btn.setFixedSize(80, 40)
        btn.clicked.connect(lambda: self._on_browse_target(category, edit))
        
        row.addWidget(edit)
        row.addWidget(btn)
        group.addLayout(row)
        return {'layout': group, 'edit': edit}

    def _create_tag_chips(self, tags, target_input):
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignLeft)
        
        for tag in tags:
            btn = QPushButton(tag)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(26)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Theme.SURFACE_LIGHT};
                    border: 1px solid {Theme.BORDER};
                    border-radius: 13px;
                    padding: 0 12px;
                    color: {Theme.TEXT_MAIN};
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {Theme.PRIMARY};
                    border-color: {Theme.PRIMARY};
                    color: white;
                }}
            """)
            btn.clicked.connect(lambda checked=False, t=tag, i=target_input: self._insert_tag(t, i))
            layout.addWidget(btn)
        return layout

    def _insert_tag(self, tag, target_input):
        text = f"{{{tag}}}"
        target_input.insert(text)
        target_input.setFocus()

    def _create_section_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: 800; font-size: 11px; letter-spacing: 1.5px;")
        return lbl

    def _create_input_group(self, label_text, value, placeholder=""):
        group = QVBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {Theme.TEXT_MAIN};")
        group.addWidget(lbl)
        
        edit = QLineEdit()
        edit.setText(value)
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(40)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background: {Theme.SURFACE_DARK};
                border: 1px solid {Theme.BORDER};
                border-radius: 6px;
                padding: 0 10px;
                color: {Theme.TEXT_MAIN};
            }}
            QLineEdit:disabled {{
                background: {Theme.SURFACE};
                color: {Theme.TEXT_DIM};
                border-color: {Theme.SURFACE_LIGHT};
            }}
        """)
        group.addWidget(edit)
        return {'layout': group, 'edit': edit}

    def _create_placeholder_tab(self, title):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(QLabel(f"<h2 style='color: white;'>{title}</h2><p style='color: gray;'>Under construction...</p>"))
        return widget

    def _on_browse_path(self):
        current = self.path_input.text()
        folder = QFileDialog.getExistingDirectory(self, "Select Default Scan Directory", current)
        if folder:
            self.path_input.setText(folder)

    def _on_browse_target(self, category, target_input):
        current = target_input.text()
        title = "Root Target" if category == 'root' else category.title()
        folder = QFileDialog.getExistingDirectory(self, f"Select Target Folder for {title}", current)
        if folder:
            target_input.setText(folder)

    def _on_save(self):
        # Update settings object
        s = self.engine.config.settings
        s.default_scan_path = self.path_input.text()
        s.target_dir_movies = self.movie_target_input['edit'].text()
        s.target_dir_shows = self.show_target_input.text()
        s.vid_size = self.size_spin.value()
        s.metadata_language = self.lang_combo.currentData()
        
        # Organization
        s.move_files = self.move_files_cb.isChecked()
        s.base_target_path = self.base_path_input['edit'].text()
        s.auto_organize_by_type = self.auto_org_cb.isChecked()
        s.movies_subfolder_name = self.movie_sub_name['edit'].text()
        s.shows_subfolder_name = self.show_sub_name['edit'].text()
        
        # Renaming
        s.custom_variable = self.custom_var_input['edit'].text()
        s.movie_template = self.movie_tpl['edit'].text()
        s.episode_template = self.episode_tpl['edit'].text()
        
        s.create_movie_folder = self.movie_folder_cb.isChecked()
        s.movie_folder_template = self.movie_folder_tpl['edit'].text()
        
        s.create_show_folder = self.show_folder_cb.isChecked()
        s.show_folder_template = self.show_folder_tpl['edit'].text()
        
        s.create_season_folder = self.season_folder_cb.isChecked()
        s.season_folder_template = self.season_folder_tpl['edit'].text()
        s.zero_padding = self.zero_pad_cb.isChecked()
        
        # Styling
        s.filename_case = self.casing_combo.currentData()
        s.separator = self.sep_combo.currentData()
        
        # Multi-Part
        s.multi_part_keyword = self.multi_kw_combo.currentText()
        s.multi_part_style = self.multi_style_combo.currentData()
        s.multi_part_position = self.multi_pos_combo.currentData()
        s.multi_part_separator = self.multi_sep_combo.currentData()
        
        # Advanced
        s.cleanup_empty_folders = self.cleanup_cb.isChecked()
        
        # API
        s.tmdb_key = self.tmdb_key_input['edit'].text()
        s.tmdb_bearer_token = self.tmdb_token_input['edit'].text()
        s.omdb_key = self.omdb_key_input['edit'].text()

        self.save_btn.setEnabled(False)
        self.save_btn.setText("Saving...")
        
        self.save_worker = SaveWorker(self.engine)
        self.save_worker.finished.connect(self._on_save_finished)
        self.save_worker.start()

    def _on_save_finished(self):
        self.save_btn.setEnabled(True)
        self.save_btn.setText("Save All Changes")
        print("Settings saved successfully.")

    def _on_lang_changed(self):
        """Ensures the same language cannot be selected as both target and fallback."""
        target_code = self.lang_combo.currentData()
        
        # Disable the target language in the fallback combo
        for i in range(self.fallback_combo.count()):
            code = self.fallback_combo.itemData(i)
            item = self.fallback_combo.model().item(i)
            if not item: continue
            
            if code == target_code and code != "":
                if self.fallback_combo.currentIndex() == i:
                    self.fallback_combo.setCurrentIndex(0) # Reset to 'None'
                item.setEnabled(False)
            else:
                item.setEnabled(True)
