from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QPushButton, QFileDialog
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab
from core.i18n import T
import os

class GeneralTab(BaseSettingsTab):
    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QLabel(T("settings.general.header"))
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)
        
        # User Info
        layout.addWidget(self._create_section_header(T("settings.general.sections.user_info")))
        self.name_input = self._create_input_group(T("settings.general.fields.display_name"), self.engine.config.settings.user_name, T("settings.general.fields.display_name_placeholder"))
        layout.addLayout(self.name_input['layout'])
 
        # Appearance
        layout.addWidget(self._create_section_header(T("settings.general.sections.appearance")))
        app_lang_layout = QVBoxLayout()
        app_lang_layout.addWidget(QLabel(T("settings.general.fields.app_lang")))
        self.app_lang_combo = QComboBox()
        self.app_lang_combo.setStyleSheet(Theme.get_combobox_style())
        self.app_lang_combo.setFixedWidth(200)
        self.app_lang_combo.addItem(T("common.languages.en"), "en")
        
        idx = self.app_lang_combo.findData(self.engine.config.settings.app_language)
        if idx >= 0: self.app_lang_combo.setCurrentIndex(idx)
        app_lang_layout.addWidget(self.app_lang_combo)
        layout.addLayout(app_lang_layout)

        # Scan Path
        layout.addWidget(self._create_section_header(T("settings.general.sections.directories")))
        self.path_group = self._create_path_input(T("settings.general.fields.scan_dir"), self.engine.config.settings.default_scan_path, "scan", self._on_browse)
        layout.addLayout(self.path_group['layout'])

        # Languages
        layout.addWidget(self._create_section_header(T("settings.general.sections.metadata")))
        lang_layout = QHBoxLayout()
        
        # Primary Language
        l1_group = QVBoxLayout()
        l1_group.addWidget(QLabel(T("settings.general.fields.primary_lang")))
        self.lang_combo = QComboBox()
        self.lang_combo.setStyleSheet(Theme.get_combobox_style())
        self.lang_combo.setFixedWidth(200)
        langs = [
            (T("common.languages.hu"), "hu-HU"), 
            (T("common.languages.en"), "en-US"), 
            (T("common.languages.de"), "de-DE"), 
            (T("common.languages.fr"), "fr-FR"),
            (T("common.languages.it"), "it-IT"),
            (T("common.languages.es"), "es-ES")
        ]
        for name, code in langs:
            self.lang_combo.addItem(name, code)
        
        idx = self.lang_combo.findData(self.engine.config.settings.metadata_language)
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        l1_group.addWidget(self.lang_combo)
        lang_layout.addLayout(l1_group)
        
        # Fallback Language
        l2_group = QVBoxLayout()
        l2_group.addWidget(QLabel(T("settings.general.fields.fallback_lang")))
        self.fallback_combo = QComboBox()
        self.fallback_combo.setStyleSheet(Theme.get_combobox_style())
        self.fallback_combo.setFixedWidth(200)
        self.fallback_combo.addItem(T("settings.general.fields.none_fallback"), "")
        for name, code in langs:
            self.fallback_combo.addItem(name, code)
            
        idx = self.fallback_combo.findData(getattr(self.engine.config.settings, 'fallback_language', ''))
        if idx >= 0: self.fallback_combo.setCurrentIndex(idx)
        l2_group.addWidget(self.fallback_combo)
        lang_layout.addLayout(l2_group)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # File Filters
        layout.addWidget(self._create_section_header(T("settings.general.sections.filters")))
        size_layout = QHBoxLayout()
        size_lbl = QLabel(T("settings.general.fields.min_size"))
        size_lbl.setFixedWidth(180)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(0, 10000)
        self.size_spin.setValue(self.engine.config.settings.vid_size)
        self.size_spin.setFixedWidth(100)
        self.size_spin.setStyleSheet(Theme.get_spinbox_style())
        size_layout.addWidget(size_lbl)
        size_layout.addWidget(self.size_spin)
        size_layout.addStretch()
        layout.addLayout(size_layout)

        layout.addStretch()

    def _on_browse(self, category, edit_field):
        current = edit_field.text()
        if not current or not os.path.exists(current):
            current = os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, T("settings.folders.fields.select_dir"), current)
        if folder:
            edit_field.setText(folder)

    def save_to_settings(self, s):
        s.user_name = self.name_input['edit'].text().strip()
        s.app_language = self.app_lang_combo.currentData()
        s.default_scan_path = self.path_group['edit'].text()
        s.metadata_language = self.lang_combo.currentData()
        s.fallback_language = self.fallback_combo.currentData()
        s.vid_size = self.size_spin.value()
