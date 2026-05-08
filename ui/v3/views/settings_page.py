import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QListWidget, QListWidgetItem, QStackedWidget)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from ui.v3.styles.theme import Theme
from core.i18n import T

# Import modular tabs
from ui.v3.views.settings.general_tab import GeneralTab
from ui.v3.views.settings.naming_tab import NamingTab
from ui.v3.views.settings.folders_tab import FoldersTab
from ui.v3.views.settings.extras_tab import ExtrasTab
from ui.v3.views.settings.api_tab import APITab
from ui.v3.views.settings.advanced_tab import AdvancedTab
from ui.v3.views.settings.view_tab import ViewTab

logger = logging.getLogger(__name__)

class SaveWorker(QThread):
    finished = Signal()
    error = Signal(str)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def run(self):
        try:
            self.engine.config.save()
            self.finished.emit()
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            self.error.emit(str(e))

class SettingsPage(QWidget):
    database_wiped = Signal()
    settings_changed = Signal()
    error_occurred = Signal(str, str) # title, message

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet(Theme.get_settings_sidebar_style())
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 30)
        sidebar_layout.setSpacing(10)

        title = QLabel(T("settings.title"))
        title.setStyleSheet(Theme.get_settings_title_style())
        sidebar_layout.addWidget(title)

        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet(Theme.get_settings_nav_list_style())
        
        items = [
            (T("settings.tabs.general"), 0, "sliders"),
            (T("settings.tabs.naming"), 1, "type"),
            (T("settings.tabs.folders"), 2, "folder"),
            (T("settings.tabs.extras"), 3, "puzzle"),
            (T("settings.tabs.api"), 4, "key"),
            (T("settings.tabs.view") or "Appearance", 5, "rocket"),
            (T("settings.tabs.advanced"), 6, "shield-alert")
        ]
        
        self.nav_list.setIconSize(QSize(18, 18))
        for label, idx, icon_name in items:
            item = QListWidgetItem(Theme.get_icon(icon_name, size=18, color=Theme.TEXT_MUTED), label)
            self.nav_list.addItem(item)
            
        sidebar_layout.addWidget(self.nav_list)
        sidebar_layout.addStretch()

        # Save Button at bottom of sidebar
        self.save_btn = QPushButton(T("settings.save_btn"))
        self.save_btn.setFixedHeight(45)
        self.save_btn.setStyleSheet(Theme.get_primary_button_style())
        self.save_btn.clicked.connect(self._on_save)
        sidebar_layout.addWidget(self.save_btn)

        layout.addWidget(self.sidebar)

        # 2. Main Content Area (Stacked Tabs)
        self.content_stack = QStackedWidget()
        
        self.tabs = [
            GeneralTab(self.engine),
            NamingTab(self.engine),
            FoldersTab(self.engine),
            ExtrasTab(self.engine),
            APITab(self.engine),
            ViewTab(self.engine),
            AdvancedTab(self.engine)
        ]
        
        for tab in self.tabs:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setStyleSheet(Theme.get_settings_content_style())
            scroll.setWidget(tab)
            self.content_stack.addWidget(scroll)
            
            # Relay signals from tabs
            if hasattr(tab, 'database_wiped'):
                tab.database_wiped.connect(self.database_wiped.emit)

        layout.addWidget(self.content_stack)
        
        # Navigation logic
        self.nav_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    def _on_save(self):
        # Gather data from all tabs
        s = self.engine.config.settings
        for tab in self.tabs:
            if hasattr(tab, 'save_to_settings'):
                tab.save_to_settings(s)
        
        self.save_btn.setEnabled(False)
        self.save_btn.setText(T("settings.saving"))
        
        self.save_worker = SaveWorker(self.engine)
        self.save_worker.finished.connect(self._on_save_finished)
        self.save_worker.error.connect(self._on_save_failed)
        self.save_worker.start()

    def _on_save_finished(self):
        self._reset_save_button()
        self.settings_changed.emit()
        logger.info("Settings saved successfully.")

    def _on_save_failed(self, error_msg):
        self._reset_save_button()
        self.error_occurred.emit("Save Error", f"Failed to save settings: {error_msg}")

    def _reset_save_button(self):
        self.save_btn.setEnabled(True)
        self.save_btn.setText(T("settings.save_btn"))

    def refresh_style(self):
        """Forces a re-application of styles to handling theme changes."""
        self.sidebar.setStyleSheet(Theme.get_settings_sidebar_style())
        self.nav_list.setStyleSheet(Theme.get_settings_nav_list_style())
        self.save_btn.setStyleSheet(Theme.get_primary_button_style())
        
        for tab in self.tabs:
            if hasattr(tab, 'refresh_style'):
                tab.refresh_style()
            # Also update scroll areas
            if isinstance(tab.parent(), QScrollArea):
                tab.parent().setStyleSheet(Theme.get_settings_content_style())

from PySide6.QtWidgets import QFrame # Ensure QFrame is available
