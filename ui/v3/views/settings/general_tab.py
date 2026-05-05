from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QPushButton, QFileDialog
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab
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

        header = QLabel("General Settings")
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)
        
        # User Info
        layout.addWidget(self._create_section_header("USER INFORMATION"))
        self.name_input = self._create_input_group("Display Name", self.engine.config.settings.user_name, "Your Name")
        layout.addLayout(self.name_input['layout'])

        # Scan Path
        layout.addWidget(self._create_section_header("DEFAULT DIRECTORIES"))
        self.path_group = self._create_path_input("Default Scan Directory", self.engine.config.settings.default_scan_path, "scan", self._on_browse)
        layout.addLayout(self.path_group['layout'])

        # Languages
        layout.addWidget(self._create_section_header("METADATA PREFERENCES"))
        lang_layout = QHBoxLayout()
        
        # Primary Language
        l1_group = QVBoxLayout()
        l1_group.addWidget(QLabel("Primary Metadata Language"))
        self.lang_combo = QComboBox()
        self.lang_combo.setFixedWidth(200)
        langs = [("Hungarian", "hu-HU"), ("English", "en-US"), ("German", "de-DE"), ("French", "fr-FR")]
        for name, code in langs:
            self.lang_combo.addItem(name, code)
        
        idx = self.lang_combo.findData(self.engine.config.settings.metadata_language)
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        l1_group.addWidget(self.lang_combo)
        lang_layout.addLayout(l1_group)
        
        # Fallback Language
        l2_group = QVBoxLayout()
        l2_group.addWidget(QLabel("Fallback Language"))
        self.fallback_combo = QComboBox()
        self.fallback_combo.setFixedWidth(200)
        self.fallback_combo.addItem("None (Disable Fallback)", "")
        for name, code in langs:
            self.fallback_combo.addItem(name, code)
            
        idx = self.fallback_combo.findData(getattr(self.engine.config.settings, 'fallback_language', ''))
        if idx >= 0: self.fallback_combo.setCurrentIndex(idx)
        l2_group.addWidget(self.fallback_combo)
        lang_layout.addLayout(l2_group)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # File Filters
        layout.addWidget(self._create_section_header("FILE FILTERS"))
        size_layout = QHBoxLayout()
        size_lbl = QLabel("Minimum Video Size (MB):")
        size_lbl.setFixedWidth(180)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(0, 10000)
        self.size_spin.setValue(self.engine.config.settings.vid_size)
        self.size_spin.setFixedWidth(100)
        self.size_spin.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border: 1px solid {Theme.BORDER}; padding: 5px;")
        size_layout.addWidget(size_lbl)
        size_layout.addWidget(self.size_spin)
        size_layout.addStretch()
        layout.addLayout(size_layout)

        layout.addStretch()

    def _on_browse(self, category, edit_field):
        current = edit_field.text()
        if not current or not os.path.exists(current):
            current = os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Directory", current)
        if folder:
            edit_field.setText(folder)

    def save_to_settings(self, s):
        s.user_name = self.name_input['edit'].text().strip()
        s.default_scan_path = self.path_group['edit'].text()
        s.metadata_language = self.lang_combo.currentData()
        s.fallback_language = self.fallback_combo.currentData()
        s.vid_size = self.size_spin.value()
