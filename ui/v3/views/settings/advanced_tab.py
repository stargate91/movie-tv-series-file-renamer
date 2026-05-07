from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab
from ui.v3.components.modern_dialog import ModernDialog
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
        if ModernDialog.confirm(
            self, 
            T("settings.advanced.fields.wipe_confirm_title"), 
            T("settings.advanced.fields.wipe_confirm_msg"),
            icon="alert"
        ):
            try:
                # Actual wipe logic
                self.engine.wipe_discovery_data()
                self.database_wiped.emit()
                ModernDialog.show_message(self, T("common.success"), T("settings.advanced.fields.wipe_success"), icon="check")
            except Exception as e:
                ModernDialog.show_message(self, T("common.error"), f"{T('settings.advanced.fields.wipe_error_msg')} {e}", icon="alert")

    def save_to_settings(self, s):
        pass
