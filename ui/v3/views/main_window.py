import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QStackedWidget, QFileDialog)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from ui.v3.styles.theme import Theme
from ui.v3.views.discovery_page import DiscoveryPage
from ui.v3.views.settings_page import SettingsPage
from core.engine.manager import RenamerEngineV3

class ScanWorker(QThread):
    progress = Signal(int, str) # progress_percent, status_text
    finished = Signal()

    def __init__(self, engine, path):
        super().__init__()
        self.engine = engine
        self.path = path

    def run(self):
        try:
            # 1. Phase: Scanning (0-20%)
            def scan_cb(text, current, total):
                if total > 0:
                    pct = int((current / total) * 20)
                    self.progress.emit(pct, f"[{current}/{total}] {text}")

            self.engine.scanner.scan_directory(self.path, progress_callback=scan_cb)
            
            # 2. Phase: Collecting (20-50%)
            def collect_cb(text, current, total):
                if total > 0:
                    pct = 20 + int((current / total) * 30)
                    self.progress.emit(pct, f"[{current}/{total}] {text}")
                else:
                    self.progress.emit(50, "No metadata to collect.")

            self.engine.collector.collect_all(progress_callback=collect_cb)
            
            # 3. Phase: Identifying (50-100%)
            def resolve_cb(text, current, total):
                if total > 0:
                    pct = 50 + int((current / total) * 50)
                    self.progress.emit(pct, f"[{current}/{total}] {text}")
                else:
                    self.progress.emit(100, "No media to identify.")

            self.engine.resolver.resolve_all(progress_callback=resolve_cb)
            
            self.progress.emit(100, "Discovery complete.")
            self.finished.emit()
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"ScanWorker Error: {e}")
            self.progress.emit(0, f"Error: {str(e)}")
            self.finished.emit()

class MainWindowV3(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = RenamerEngineV3()
        self.active_workers = [] # Prevent ScanWorker GC crash
        
        self.setWindowTitle("RENDA - Smart Media Organizer")
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
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # 2. Main Content Area
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        # Create Views
        self.dashboard_view = self._create_dashboard_view()
        self.discovery_page = DiscoveryPage(self.engine)
        self.library_view = QWidget() # Placeholder
        self.history_view = QWidget() # Placeholder
        self.settings_view = SettingsPage(self.engine)

        self.content_stack.addWidget(self.dashboard_view)
        self.content_stack.addWidget(self.discovery_page)
        self.content_stack.addWidget(self.library_view)
        self.content_stack.addWidget(self.history_view)
        self.content_stack.addWidget(self.settings_view)

        # Connect Sidebar Buttons
        self.btn_dash.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
        self.btn_lib.clicked.connect(self._on_library_clicked)
        self.btn_hist.clicked.connect(lambda: self.content_stack.setCurrentIndex(3))
        self.btn_sett.clicked.connect(lambda: self.content_stack.setCurrentIndex(4))

        # Connect Discovery View Buttons
        self.discovery_page.scan_new_btn.clicked.connect(self._on_scan_clicked)

    def _on_library_clicked(self):
        """Switches to Library/Discovery page and auto-loads data."""
        self.content_stack.setCurrentIndex(1)
        self.discovery_page.refresh_data()

    def _on_scan_clicked(self):
        import os
        # Use default path from settings if available, else user's home directory
        start_dir = self.engine.config.settings.default_scan_path
        if not start_dir or not os.path.exists(start_dir):
            start_dir = os.path.expanduser("~")
            
        folder = QFileDialog.getExistingDirectory(self, "Select Media Directory", start_dir)
        if folder:
            self._start_scan(folder)

    def _start_scan(self, path):
        # 1. Update Navigation Buttons
        self.btn_dash.setChecked(False)
        self.btn_lib.setChecked(True)
        
        # 2. Prepare UI
        self.content_stack.setCurrentWidget(self.discovery_page)
        self.discovery_page.progress_bar.show()
        self.discovery_page.status_info.show()
        self.discovery_page.progress_bar.setValue(0)
        self.discovery_page.status_info.setText("Initializing...")
        
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

    def _create_sidebar(self):
        frame = QFrame()
        frame.setObjectName("Sidebar")
        frame.setFixedWidth(220)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 25, 15, 25)
        layout.setSpacing(10)

        # Logo / App Name
        title = QLabel("RENDA")
        title.setStyleSheet(Theme.get_sidebar_title_style())
        
        subtitle = QLabel("Smart Media Organizer")
        subtitle.setStyleSheet(Theme.get_sidebar_subtitle_style())
        
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Nav Buttons
        self.btn_dash = self._create_nav_btn("Dashboard", True)
        self.btn_lib = self._create_nav_btn("Library", False)
        self.btn_hist = self._create_nav_btn("History", False)
        self.btn_sett = self._create_nav_btn("Settings", False)

        layout.addWidget(self.btn_dash)
        layout.addWidget(self.btn_lib)
        layout.addWidget(self.btn_hist)
        layout.addStretch()

        # Restart Button
        self.btn_restart = QPushButton("  Restart App")
        self.btn_restart.setObjectName("SecondaryButton")
        self.btn_restart.setFixedHeight(40)
        self.btn_restart.setCursor(Qt.PointingHandCursor)
        self.btn_restart.clicked.connect(self._on_restart_clicked)
        layout.addWidget(self.btn_restart)
        layout.addSpacing(10)

        layout.addWidget(self.btn_sett)

        return frame

    def _on_restart_clicked(self):
        """Restarts the application to apply code changes."""
        import os
        import sys
        # os.execl replaces the current process with a new one
        os.execl(sys.executable, sys.executable, *sys.argv)

    def _create_nav_btn(self, text, active=False):
        btn = QPushButton(f"  {text}") # Space for icon simulation
        btn.setObjectName("NavButton")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setChecked(active)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(45)
        return btn

    def _create_dashboard_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(40, 40, 40, 40)
        
        import datetime
        current_hour = datetime.datetime.now().hour
        if 5 <= current_hour < 12:
            greeting_time = "Good morning"
        elif 12 <= current_hour < 18:
            greeting_time = "Good afternoon"
        elif 18 <= current_hour < 22:
            greeting_time = "Good evening"
        else:
            greeting_time = "Good night"

        user_name = self.engine.config.settings.user_name
        if user_name:
            greeting = f"{greeting_time}, {user_name}!"
        else:
            greeting = f"{greeting_time},"

        # Welcome Header
        header = QLabel(greeting)
        header.setStyleSheet(Theme.get_h2_style())
        
        sub_header = QLabel("Ready to organize your library?")
        sub_header.setStyleSheet(Theme.get_h1_style())
        
        layout.addWidget(header)
        layout.addWidget(sub_header)
        layout.addSpacing(40)
        
        # Action Card (The Big Scan Button)
        scan_card = QFrame()
        scan_card.setStyleSheet(Theme.get_card_style())
        scan_card.setFixedHeight(200)
        
        card_layout = QVBoxLayout(scan_card)
        card_layout.setAlignment(Qt.AlignCenter)
        
        scan_btn = QPushButton("Scan Directory")
        scan_btn.setFixedSize(200, 50)
        scan_btn.setCursor(Qt.PointingHandCursor)
        scan_btn.clicked.connect(self._on_scan_clicked)
        
        card_layout.addWidget(scan_btn)
        
        layout.addWidget(scan_card)
        layout.addStretch()
        
        return view

def start_v3_ui():
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindowV3()
    window.showMaximized()
    sys.exit(app.exec())
