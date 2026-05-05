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

        # --- Section: Basic Logic ---
        layout.addWidget(self._create_section_header(T("settings.folders.sections.logic")))
        self.move_files_cb = QCheckBox(T("settings.folders.fields.move_files"))
        self.move_files_cb.setChecked(self.engine.config.settings.move_files)
        self.move_files_cb.setStyleSheet("font-size: 14px; color: white;")
        layout.addWidget(self.move_files_cb)

        self.base_path_input = self._create_path_input(T("settings.folders.fields.root_path"), self.engine.config.settings.base_target_path, "root", self._on_browse)
        layout.addLayout(self.base_path_input['layout'])
        self.base_path_input['edit'].setEnabled(self.engine.config.settings.move_files)
        self.move_files_cb.toggled.connect(self.base_path_input['edit'].setEnabled)

        layout.addSpacing(10)
        layout.addWidget(Theme.create_hline())

        # --- Section: Automatic Sorting ---
        layout.addWidget(self._create_section_header(T("settings.folders.sections.sorting")))
        self.auto_org_cb = QCheckBox(T("settings.folders.fields.auto_sort"))
        self.auto_org_cb.setChecked(self.engine.config.settings.auto_organize_by_type)
        layout.addWidget(self.auto_org_cb)

        sort_row = QHBoxLayout()
        self.movie_sub_name = self._create_input_group(T("settings.folders.fields.movies_sub"), self.engine.config.settings.movies_subfolder_name, "Movies")
        self.show_sub_name = self._create_input_group(T("settings.folders.fields.shows_sub"), self.engine.config.settings.shows_subfolder_name, "TV Shows")
        sort_row.addLayout(self.movie_sub_name['layout'])
        sort_row.addLayout(self.show_sub_name['layout'])
        layout.addLayout(sort_row)

        self.auto_org_cb.toggled.connect(self.movie_sub_name['edit'].setEnabled)
        self.auto_org_cb.toggled.connect(self.show_sub_name['edit'].setEnabled)
        
        layout.addSpacing(15)
        layout.addWidget(Theme.create_hline())

        # --- Section: Folder Templates ---
        layout.addWidget(self._create_section_header(T("settings.folders.sections.templates")))
        
        # Movies
        self.movie_folder_cb = QCheckBox(T("settings.folders.fields.movie_folder"))
        self.movie_folder_cb.setChecked(self.engine.config.settings.create_movie_folder)
        layout.addWidget(self.movie_folder_cb)
        self.movie_folder_tpl = self._create_input_group(T("settings.folders.fields.movie_tpl"), self.engine.config.settings.movie_folder_template, "{Title} ({Year})")
        layout.addLayout(self.movie_folder_tpl['layout'])
        
        # TV Shows
        layout.addSpacing(10)
        self.show_folder_cb = QCheckBox(T("settings.folders.fields.show_folder"))
        self.show_folder_cb.setChecked(self.engine.config.settings.create_show_folder)
        layout.addWidget(self.show_folder_cb)
        self.show_folder_tpl = self._create_input_group(T("settings.folders.fields.show_tpl"), self.engine.config.settings.show_folder_template, "{ShowTitle}")
        layout.addLayout(self.show_folder_tpl['layout'])

        self.season_folder_cb = QCheckBox(T("settings.folders.fields.season_folder"))
        self.season_folder_cb.setChecked(self.engine.config.settings.create_season_folder)
        layout.addWidget(self.season_folder_cb)
        self.season_folder_tpl = self._create_input_group(T("settings.folders.fields.season_tpl"), self.engine.config.settings.season_folder_template, "Season {Season}")
        layout.addLayout(self.season_folder_tpl['layout'])

        layout.addStretch()

    def save_to_settings(self, s):
        s.move_files = self.move_files_cb.isChecked()
        s.base_target_path = self.base_path_input['edit'].text()
        s.auto_organize_by_type = self.auto_org_cb.isChecked()
        s.movies_subfolder_name = self.movie_sub_name['edit'].text()
        s.shows_subfolder_name = self.show_sub_name['edit'].text()
        s.create_movie_folder = self.movie_folder_cb.isChecked()
        s.movie_folder_template = self.movie_folder_tpl['edit'].text()
        s.create_show_folder = self.show_folder_cb.isChecked()
        s.show_folder_template = self.show_folder_tpl['edit'].text()
        s.create_season_folder = self.season_folder_cb.isChecked()
        s.season_folder_template = self.season_folder_tpl['edit'].text()

    def _on_browse(self, category, edit_field):
        current = edit_field.text()
        if not current or not os.path.exists(current):
            current = os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, T("settings.folders.fields.select_dir"), current)
        if folder:
            edit_field.setText(folder)
