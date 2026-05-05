import sys
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

class MainWindowV3(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = RenamerEngineV3()
        
        # Initialize i18n
        from core.i18n import Translator
        Translator().set_language(self.engine.config.settings.app_language)
        
        self.active_workers = [] # Prevent ScanWorker GC crash
        
        self.setWindowTitle(f"{T('app.name')} - {T('app.subtitle')}")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(Theme.get_main_stylesheet())
        
        self._init_ui()

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
        self.settings_view.database_wiped.connect(self.discovery_page.refresh_data)

    def _on_nav_requested(self, index):
        self.content_stack.setCurrentIndex(index)
        if index == 3: # History
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
        self.discovery_page.progress_bar.setValue(val)
        self.discovery_page.status_info.setText(text)

    def _on_scan_finished(self):
        # We don't remove from active_workers here; let deleteLater handle it
        self.discovery_page.progress_bar.hide()
        self.discovery_page.status_info.hide()
        self.discovery_page.refresh_data()

    def _on_restart_clicked(self):
        """Restarts the application to apply code changes."""
        import os
        import sys
        # os.execl replaces the current process with a new one
        os.execl(sys.executable, sys.executable, *sys.argv)

def start_v3_ui():
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    window = MainWindowV3()
    window.showMaximized()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    start_v3_ui()
