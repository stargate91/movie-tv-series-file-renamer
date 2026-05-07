from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QFileDialog, QFrame, QWidget
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab
from core.i18n import T
import os

class FoldersTab(BaseSettingsTab):
    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        header = QLabel(T("settings.folders.header"))
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)

        # --- Master Toggle ---
        self.enable_folders_cb = QCheckBox(T("settings.folders.fields.enable_folders"))
        self.enable_folders_cb.setStyleSheet(Theme.get_master_toggle_style())
        self.enable_folders_cb.setChecked(self.engine.config.settings.enable_folders)
        layout.addWidget(self.enable_folders_cb)

        layout.addSpacing(10)

        # --- Content Container ---
        self.content_container = QWidget()
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(25)
        layout.addWidget(self.content_container)

        # --- Section: Basic Logic ---
        content_layout.addWidget(self._create_section_header(T("settings.folders.sections.logic")))
        self.move_files_cb = QCheckBox(T("settings.folders.fields.move_files"))
        self.move_files_cb.setChecked(self.engine.config.settings.move_files)
        # Style is handled by global theme
        content_layout.addWidget(self.move_files_cb)

        self.base_path_input = self._create_path_input(T("settings.folders.fields.root_path"), self.engine.config.settings.base_target_path, "root", self._on_browse)
        content_layout.addLayout(self.base_path_input['layout'])
        self.base_path_input['edit'].setEnabled(self.engine.config.settings.move_files)
        self.move_files_cb.toggled.connect(self.base_path_input['edit'].setEnabled)

        content_layout.addSpacing(10)
        content_layout.addWidget(Theme.create_hline())

        # --- Section: Automatic Sorting ---
        content_layout.addWidget(self._create_section_header(T("settings.folders.sections.sorting")))
        self.auto_org_cb = QCheckBox(T("settings.folders.fields.auto_sort"))
        self.auto_org_cb.setChecked(self.engine.config.settings.auto_organize_by_type)
        content_layout.addWidget(self.auto_org_cb)

        sort_row = QHBoxLayout()
        self.movie_sub_name = self._create_input_group(T("settings.folders.fields.movies_sub"), self.engine.config.settings.movies_subfolder_name, "Movies")
        self.show_sub_name = self._create_input_group(T("settings.folders.fields.shows_sub"), self.engine.config.settings.shows_subfolder_name, "TV Shows")
        sort_row.addLayout(self.movie_sub_name['layout'])
        sort_row.addLayout(self.show_sub_name['layout'])
        content_layout.addLayout(sort_row)

        self.auto_org_cb.toggled.connect(self.movie_sub_name['edit'].setEnabled)
        self.auto_org_cb.toggled.connect(self.show_sub_name['edit'].setEnabled)
        
        content_layout.addSpacing(15)
        content_layout.addWidget(Theme.create_hline())

        # --- Section: Folder Templates ---
        content_layout.addWidget(self._create_section_header(T("settings.folders.sections.templates")))
        
        hint_row = QHBoxLayout()
        hint_row.setSpacing(6)
        hint_icon = QLabel()
        hint_icon.setPixmap(Theme.get_pixmap("lightbulb", size=16, color=Theme.TEXT_DIM))
        hint_icon.setStyleSheet("background: transparent; border: none;")
        hint_icon.setFixedSize(16, 16)
        hint_text = QLabel(T("settings.naming.fields.template_hint"))
        hint_text.setWordWrap(True)
        hint_text.setStyleSheet(Theme.get_hint_style())
        hint_row.addWidget(hint_icon)
        hint_row.addWidget(hint_text, 1)
        content_layout.addLayout(hint_row)
        
        # Movies
        self.movie_folder_cb = QCheckBox(T("settings.folders.fields.movie_folder") or "Create Movie Folder")
        self.movie_folder_cb.setChecked(self.engine.config.settings.create_movie_folder)
        content_layout.addWidget(self.movie_folder_cb)
        self.movie_folder_tpl = self._create_input_group(T("settings.folders.fields.movie_tpl") or "Movie Folder Template", self.engine.config.settings.movie_folder_template, "{Title} ({Year})", context="movie")
        content_layout.addLayout(self.movie_folder_tpl['layout'])
        
        # Collections (Box Sets)
        content_layout.addSpacing(10)
        self.collection_folder_cb = QCheckBox(T("settings.folders.fields.coll_folder"))
        self.collection_folder_cb.setChecked(self.engine.config.settings.create_collection_folder)
        content_layout.addWidget(self.collection_folder_cb)
        self.collection_folder_tpl = self._create_input_group(T("settings.folders.fields.coll_tpl"), self.engine.config.settings.collection_folder_template, "{Collection}", context="collection")
        content_layout.addLayout(self.collection_folder_tpl['layout'])
        
        def update_collection_state():
            self.collection_folder_tpl['edit'].setEnabled(self.collection_folder_cb.isChecked())
            
        self.collection_folder_cb.toggled.connect(update_collection_state)
        update_collection_state()
        
        # TV Shows
        content_layout.addSpacing(10)
        self.show_folder_cb = QCheckBox(T("settings.folders.fields.show_folder"))
        self.show_folder_cb.setChecked(self.engine.config.settings.create_show_folder)
        content_layout.addWidget(self.show_folder_cb)
        self.show_folder_tpl = self._create_input_group(T("settings.folders.fields.show_tpl"), self.engine.config.settings.show_folder_template, "{ShowTitle}", context="series")
        content_layout.addLayout(self.show_folder_tpl['layout'])

        self.season_folder_cb = QCheckBox(T("settings.folders.fields.season_folder") or "Create Season Folder")
        self.season_folder_cb.setChecked(self.engine.config.settings.create_season_folder)
        content_layout.addWidget(self.season_folder_cb)
        self.season_folder_tpl = self._create_input_group(T("settings.folders.fields.season_tpl") or "Season Folder Template", self.engine.config.settings.season_folder_template, "Season {Season}", context="season")
        content_layout.addLayout(self.season_folder_tpl['layout'])

        # Episodes
        content_layout.addSpacing(10)
        self.episode_folder_cb = QCheckBox(T("settings.folders.fields.episode_folder"))
        self.episode_folder_cb.setChecked(self.engine.config.settings.create_episode_folder)
        content_layout.addWidget(self.episode_folder_cb)
        self.episode_folder_tpl = self._create_input_group(T("settings.folders.fields.episode_tpl"), self.engine.config.settings.episode_folder_template, "{ShowTitle} - {Season}{Episode}", context="tv")
        content_layout.addLayout(self.episode_folder_tpl['layout'])
        
        def update_episode_state():
            self.episode_folder_tpl['edit'].setEnabled(self.episode_folder_cb.isChecked())
            
        self.episode_folder_cb.toggled.connect(update_episode_state)
        update_episode_state()

        content_layout.addSpacing(15)
        content_layout.addWidget(Theme.create_hline())

        # --- Section: Post-Processing ---
        content_layout.addWidget(self._create_section_header(T("settings.advanced.sections.cleanup") or "Post-Processing Cleanup"))
        self.cleanup_cb = QCheckBox(T("settings.advanced.fields.cleanup_folders") or "Remove empty folders after moving files")
        self.cleanup_cb.setChecked(self.engine.config.settings.cleanup_empty_folders)
        content_layout.addWidget(self.cleanup_cb)
        
        # Link master toggle to container
        self.enable_folders_cb.toggled.connect(self.content_container.setEnabled)
        self.content_container.setEnabled(self.engine.config.settings.enable_folders)

        layout.addStretch()

    def save_to_settings(self, s):
        s.enable_folders = self.enable_folders_cb.isChecked()
        s.move_files = self.move_files_cb.isChecked()
        s.base_target_path = self.base_path_input['edit'].text()
        s.auto_organize_by_type = self.auto_org_cb.isChecked()
        s.movies_subfolder_name = self.movie_sub_name['edit'].text()
        s.shows_subfolder_name = self.show_sub_name['edit'].text()
        s.create_movie_folder = self.movie_folder_cb.isChecked()
        s.movie_folder_template = self.movie_folder_tpl['edit'].text()
        s.create_collection_folder = self.collection_folder_cb.isChecked()
        s.collection_folder_template = self.collection_folder_tpl['edit'].text()
        s.create_show_folder = self.show_folder_cb.isChecked()
        s.show_folder_template = self.show_folder_tpl['edit'].text()
        s.create_season_folder = self.season_folder_cb.isChecked()
        s.season_folder_template = self.season_folder_tpl['edit'].text()
        s.create_episode_folder = self.episode_folder_cb.isChecked()
        s.episode_folder_template = self.episode_folder_tpl['edit'].text()
        s.cleanup_empty_folders = self.cleanup_cb.isChecked()

    def _on_browse(self, category, edit_field):
        current = edit_field.text()
        if not current or not os.path.exists(current):
            current = os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, T("settings.folders.fields.select_dir"), current)
        if folder:
            edit_field.setText(folder)
