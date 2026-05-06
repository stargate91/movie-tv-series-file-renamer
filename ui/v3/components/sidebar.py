from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal
from ui.v3.styles.theme import Theme
from core.i18n import T

class Sidebar(QFrame):
    """
    Vertical navigation sidebar for the application.
    Emits signals when navigation items are selected.
    """
    nav_requested = Signal(int) # index of the view to switch to
    restart_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)
        self._init_ui()

    def _init_ui(self):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl, QCoreApplication
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 25, 15, 25)
        layout.setSpacing(10)

        # 1. Branding
        title = QLabel(T("app.name"))
        title.setStyleSheet(Theme.get_sidebar_title_style())
        
        subtitle = QLabel(T("app.subtitle"))
        subtitle.setStyleSheet(Theme.get_sidebar_subtitle_style())
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        # 2. Navigation Area (Top)
        self.btn_dash = self._create_nav_btn(T("sidebar.dashboard"), 0, True)
        self.btn_lib = self._create_nav_btn(T("sidebar.library"), 1)
        self.btn_hist = self._create_nav_btn(T("sidebar.history"), 3)
        self.btn_sett = self._create_nav_btn(T("sidebar.settings"), 4)
        
        layout.addWidget(self.btn_dash)
        layout.addWidget(self.btn_lib)
        layout.addWidget(self.btn_hist)
        layout.addWidget(self.btn_sett)
        
        # 3. Support Button (Part of Navigation)
        self.btn_support = QPushButton(T("sidebar.support"))
        self.btn_support.setStyleSheet(Theme.get_support_button_style())
        self.btn_support.setFixedHeight(45)
        self.btn_support.setCursor(Qt.PointingHandCursor)
        self.btn_support.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://buymeacoffee.com/majtika")))
        layout.addWidget(self.btn_support)

        layout.addStretch()

        # 4. System Actions (Bottom)
        self.btn_restart = QPushButton(T('sidebar.restart'))
        self.btn_restart.setObjectName("SecondaryButton")
        self.btn_restart.setFixedHeight(45)
        self.btn_restart.setCursor(Qt.PointingHandCursor)
        self.btn_restart.clicked.connect(self.restart_requested.emit)
        
        self.btn_quit = QPushButton(T('common.quit'))
        self.btn_quit.setObjectName("SecondaryButton") # Reuse styling
        self.btn_quit.setFixedHeight(45)
        self.btn_quit.setCursor(Qt.PointingHandCursor)
        self.btn_quit.clicked.connect(QCoreApplication.quit)
        
        layout.addWidget(self.btn_restart)
        layout.addWidget(self.btn_quit)

    def _create_nav_btn(self, text, index, active=False):
        btn = QPushButton(text)
        btn.setObjectName("NavButton")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setChecked(active)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(45)
        btn.clicked.connect(lambda: self.nav_requested.emit(index))
        return btn

    def set_active(self, index):
        """Programmatically switches the active button state."""
        buttons = {
            0: self.btn_dash,
            1: self.btn_lib,
            3: self.btn_hist,
            4: self.btn_sett
        }
        if index in buttons:
            buttons[index].setChecked(True)
