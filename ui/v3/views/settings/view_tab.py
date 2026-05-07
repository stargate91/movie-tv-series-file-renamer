from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QFrame)
from PySide6.QtCore import Qt, Signal
from ui.v3.styles.theme import Theme
from core.i18n import T
from .base_tab import BaseSettingsTab

class ViewTab(BaseSettingsTab):
    """
    Appearance and Theme settings.
    """
    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Header
        header = QLabel(T("settings.view.header") or "Application Appearance")
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)

        # 1. Theme Selection
        layout.addWidget(self._create_section_header(T("settings.view.theme_title") or "Theme & Style"))
        
        theme_lay = QVBoxLayout()
        theme_lay.setSpacing(10)
        theme_lay.addWidget(QLabel(T("settings.view.theme_label") or "Application Theme:"))
        
        self.combo_theme = QComboBox()
        self.combo_theme.setStyleSheet(Theme.get_combobox_style())
        self.combo_theme.setFixedWidth(240)
        self.combo_theme.setFixedHeight(40)
        self.combo_theme.addItem(T("settings.view.theme_light") or "Standard Light", "light")
        self.combo_theme.addItem(T("settings.view.theme_dark") or "Premium Dark", "dark")
        
        # Load current
        current_theme = self.engine.config.settings.ui_theme
        idx = self.combo_theme.findData(current_theme)
        if idx >= 0: self.combo_theme.setCurrentIndex(idx)
        
        theme_lay.addWidget(self.combo_theme)
        layout.addLayout(theme_lay)

        # 2. Icon Style Information
        layout.addSpacing(10)
        layout.addWidget(self._create_section_header(T("settings.view.icons_title") or "Interface Details"))
        
        hint_lbl = QLabel(T("settings.view.icons_msg") or "Modern Lucide icons are used throughout the application to ensure clarity.")
        hint_lbl.setStyleSheet(Theme.get_hint_style())
        hint_lbl.setWordWrap(True)
        layout.addWidget(hint_lbl)

        layout.addStretch()

    def save_to_settings(self, settings):
        settings.ui_theme = self.combo_theme.currentData()
