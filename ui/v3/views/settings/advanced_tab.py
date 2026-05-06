from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab
from core.i18n import T

class AdvancedTab(BaseSettingsTab):
    database_wiped = Signal()

    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QLabel(T("settings.advanced.header"))
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)

        # --- Section: Multi-Part ---
        layout.addWidget(self._create_section_header(T("settings.advanced.sections.multi_part")))
        self.multi_kw_combo = QComboBox()
        self.multi_kw_combo.addItems(["Part", "CD", "Disk", "pt"])
        self.multi_kw_combo.setEditable(True)
        self.multi_kw_combo.setCurrentText(self.engine.config.settings.multi_part_keyword)
        
        kw_layout = QHBoxLayout()
        kw_layout.addWidget(QLabel(T("settings.advanced.fields.part_keyword")))
        kw_layout.addWidget(self.multi_kw_combo)
        kw_layout.addStretch()
        layout.addLayout(kw_layout)

        # --- Section: Cleanup ---
        layout.addWidget(self._create_section_header(T("settings.advanced.sections.cleanup")))
        self.cleanup_cb = QCheckBox(T("settings.advanced.fields.cleanup_folders"))
        self.cleanup_cb.setChecked(self.engine.config.settings.cleanup_empty_folders)
        layout.addWidget(self.cleanup_cb)

        # --- Section: Danger Zone ---
        layout.addSpacing(40)
        layout.addWidget(self._create_section_header(T("settings.advanced.sections.danger")))
        
        danger_desc = QLabel(T("settings.advanced.fields.wipe_desc"))
        danger_desc.setWordWrap(True)
        danger_desc.setStyleSheet(Theme.get_card_description_style())
        layout.addWidget(danger_desc)
        
        self.wipe_btn = QPushButton(T("settings.advanced.fields.wipe_btn"))
        self.wipe_btn.setFixedSize(200, 40)
        self.wipe_btn.setStyleSheet(Theme.get_danger_ghost_button_style())
        self.wipe_btn.clicked.connect(self._on_wipe_database)
        layout.addWidget(self.wipe_btn)

        layout.addStretch()

    def _on_wipe_database(self):
        reply = QMessageBox.question(
            self, T("settings.advanced.fields.wipe_confirm_title"), 
            T("settings.advanced.fields.wipe_confirm_msg"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Actual wipe logic
                self.engine.db.wipe_discovery_data()
                self.database_wiped.emit()
                QMessageBox.information(self, T("common.success"), T("settings.advanced.fields.wipe_success"))
            except Exception as e:
                QMessageBox.critical(self, T("common.error"), f"{T('settings.advanced.fields.wipe_error_msg')} {e}")

    def save_to_settings(self, s):
        s.multi_part_keyword = self.multi_kw_combo.currentText()
        s.cleanup_empty_folders = self.cleanup_cb.isChecked()
