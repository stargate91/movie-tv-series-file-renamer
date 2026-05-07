import sys
import logging
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QStackedWidget, QFileDialog)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from ui.v3.styles.theme import Theme
from ui.v3.views.discovery_page import DiscoveryPage
from ui.v3.views.settings_page import SettingsPage
from ui.v3.views.dashboard_page import DashboardPage
from ui.v3.views.history_page import HistoryPage
from ui.v3.components.sidebar import Sidebar
from ui.v3.workers.scan_worker import ScanWorker
from core.engine.manager import RenamerEngineV3
from core.i18n import T

logger = logging.getLogger(__name__)

class MainWindowV3(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = RenamerEngineV3()
        
        # Initialize i18n
        from core.i18n import Translator
        Translator().load_locale(self.engine.config.settings.app_language)
        
        self.active_workers = [] # Prevent ScanWorker GC crash
        
        self.setWindowTitle(f"{T('app.name')} - {T('app.subtitle')}")
        self.setMinimumSize(1100, 700)
        
        # Apply initial theme
        self._apply_theme(self.engine.config.settings.ui_theme)
        
        self._init_ui()
        self._last_lang = self.engine.config.settings.metadata_language

    def _init_ui(self):
        # Main container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        # 2. Main Content Area
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        # Create Views
        self.dashboard_page = DashboardPage(self.engine)
        self.discovery_page = DiscoveryPage(self.engine)
        self.library_view = QWidget() # Placeholder
        self.history_page = HistoryPage(self.engine)
        self.settings_view = SettingsPage(self.engine)

        self.content_stack.addWidget(self.dashboard_page)
        self.content_stack.addWidget(self.discovery_page)
        self.content_stack.addWidget(self.library_view)
        self.content_stack.addWidget(self.history_page)
        self.content_stack.addWidget(self.settings_view)

        # Connect Sidebar
        self.sidebar.nav_requested.connect(self._on_nav_requested)
        self.sidebar.restart_requested.connect(self._on_restart_clicked)

        # Connect Child Page Signals
        self.dashboard_page.scan_clicked.connect(self._on_scan_clicked)
        
        # Connect Settings Signals
        self.settings_view.database_wiped.connect(self._on_database_wiped)
        self.settings_view.settings_changed.connect(self._on_settings_changed)

    def _on_database_wiped(self):
        """Refreshes all pages when database is wiped."""
        self.discovery_page.refresh_data()
        self.dashboard_page.refresh_data()
        self.history_page.refresh_data()

    def _on_settings_changed(self):
        """Called when settings are saved."""
        # 1. Update Theme
        new_theme = self.engine.config.settings.ui_theme
        self._apply_theme(new_theme)
        
        # 2. Check for Language Change
        new_lang = self.engine.config.settings.metadata_language
        if new_lang != self._last_lang:
            self._last_lang = new_lang
            if hasattr(self.discovery_page, 'notify_language_changed'):
                self.discovery_page.notify_language_changed(new_lang)
        
        # 3. Refresh Data
        self.discovery_page.refresh_data()
        self.dashboard_page.refresh_data()

    def _apply_theme(self, mode):
        """Updates the global palette and refreshes the stylesheet."""
        Theme.apply_theme(mode)
        
        # 1. Update Global Stylesheet
        self.setStyleSheet(Theme.get_main_stylesheet())
        
        # 2. Propagate to Sidebar
        if hasattr(self, 'sidebar'):
            self.sidebar.refresh_style()
            
        # 3. Propagate to Content Pages
        if hasattr(self, 'discovery_page'):
            self.discovery_page.refresh_style()
        if hasattr(self, 'dashboard_page') and hasattr(self.dashboard_page, 'refresh_style'):
            self.dashboard_page.refresh_style()
        if hasattr(self, 'history_page') and hasattr(self.history_page, 'refresh_style'):
            self.history_page.refresh_style()
        if hasattr(self, 'settings_view') and hasattr(self.settings_view, 'refresh_style'):
            self.settings_view.refresh_style()
            
        logger.info(f"Theme applied: {mode}")

    def _on_nav_requested(self, index):
        self.content_stack.setCurrentIndex(index)
        if index == 0: # Dashboard
            self.dashboard_page.refresh_data()
        elif index == 3: # History
            self.history_page.refresh_data()

    def _on_scan_clicked(self):
        import os
        # Use default path from settings if available, else user's home directory
        start_dir = self.engine.config.settings.default_scan_path
        if not start_dir or not os.path.exists(start_dir):
            start_dir = os.path.expanduser("~")
            
        folder = QFileDialog.getExistingDirectory(self, T("discovery.messages.select_dir"), start_dir)
        if folder:
            self._start_scan(folder)

    def _start_scan(self, path):
        # 1. Update Navigation Buttons
        self.sidebar.set_active(1) # Switch to Library
        
        # 2. Prepare UI
        self.content_stack.setCurrentWidget(self.discovery_page)
        self.discovery_page.progress_container.show()
        self.discovery_page.progress_bar.setRange(0, 100)
        self.discovery_page.progress_bar.show()
        self.discovery_page.status_info.show()
        self.discovery_page.progress_bar.setValue(0)
        self.discovery_page.status_info.setText(T("discovery.messages.initializing"))
        
        # 3. Create and Start Worker
        self.worker = ScanWorker(self.engine, path)
        self.active_workers.append(self.worker)
        self.worker.progress.connect(self._on_scan_progress)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _on_scan_progress(self, val, text):
        # Ensure we are not in indeterminate mode
        if self.discovery_page.progress_bar.maximum() == 0:
            self.discovery_page.progress_bar.setRange(0, 100)
            
        self.discovery_page.progress_bar.setValue(val)
        self.discovery_page.status_info.setText(text)

    def _on_scan_finished(self):
        # We don't remove from active_workers here; let deleteLater handle it
        self.discovery_page.progress_bar.hide()
        self.discovery_page.status_info.hide()
        self.discovery_page.refresh_data()
        
        # Check for API limits
        if self.engine.has_omdb_limit_reached:
            from PySide6.QtWidgets import QMessageBox
            msg = T("discovery.messages.api_limit_reached")
            QMessageBox.warning(self, T("common.warning"), msg)

    def _on_restart_clicked(self):
        """Restarts the application to apply code changes."""
        import sys
        import subprocess
        from PySide6.QtCore import QCoreApplication
        
        # Launch new instance detached
        subprocess.Popen([sys.executable] + sys.argv)
        # Gracefully quit current instance to let threads/DB close
        QCoreApplication.quit()

def start_v3_ui():
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    window = MainWindowV3()
    window.showMaximized()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    start_v3_ui()
