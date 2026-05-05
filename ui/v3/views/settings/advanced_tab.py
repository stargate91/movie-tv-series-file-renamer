from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab

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

        header = QLabel("Advanced Engine Settings")
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)

        # --- Section: Multi-Part ---
        layout.addWidget(self._create_section_header("MULTI-PART FILE HANDLING"))
        self.multi_kw_combo = QComboBox()
        self.multi_kw_combo.addItems(["Part", "CD", "Disk", "pt"])
        self.multi_kw_combo.setEditable(True)
        self.multi_kw_combo.setCurrentText(self.engine.config.settings.multi_part_keyword)
        
        kw_layout = QHBoxLayout()
        kw_layout.addWidget(QLabel("Part Keyword:"))
        kw_layout.addWidget(self.multi_kw_combo)
        kw_layout.addStretch()
        layout.addLayout(kw_layout)

        # --- Section: Cleanup ---
        layout.addWidget(self._create_section_header("POST-RENAME ACTIONS"))
        self.cleanup_cb = QCheckBox("Remove empty folders after moving files")
        self.cleanup_cb.setChecked(self.engine.config.settings.cleanup_empty_folders)
        layout.addWidget(self.cleanup_cb)

        # --- Section: Danger Zone ---
        layout.addSpacing(40)
        layout.addWidget(self._create_section_header("DANGER ZONE"))
        
        danger_desc = QLabel("Clears all indexed files, matches, and metadata from the local database. Your physical files will NOT be affected.")
        danger_desc.setWordWrap(True)
        danger_desc.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(danger_desc)
        
        self.wipe_btn = QPushButton("Wipe Local Database")
        self.wipe_btn.setFixedSize(200, 40)
        self.wipe_btn.setStyleSheet("""
            QPushButton { 
                background: #442222; border: 1px solid #663333; color: #ff8888; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background: #663333; }
        """)
        self.wipe_btn.clicked.connect(self._on_wipe_database)
        layout.addWidget(self.wipe_btn)

        layout.addStretch()

    def _on_wipe_database(self):
        reply = QMessageBox.question(
            self, "Wipe Database", 
            "Are you sure? This will clear all discovery data and history.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Actual wipe logic
                self.engine.db.wipe_discovery_data()
                self.database_wiped.emit()
                QMessageBox.information(self, "Success", "Database has been wiped.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to wipe database: {e}")

    def save_to_settings(self, s):
        s.multi_part_keyword = self.multi_kw_combo.currentText()
        s.cleanup_empty_folders = self.cleanup_cb.isChecked()
