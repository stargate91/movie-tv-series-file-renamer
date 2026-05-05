from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal
from ui.v3.styles.theme import Theme

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 25, 15, 25)
        layout.setSpacing(10)

        # 1. Branding
        title = QLabel("RENDA")
        title.setStyleSheet(Theme.get_sidebar_title_style())
        
        subtitle = QLabel("Smart Media Organizer")
        subtitle.setStyleSheet(Theme.get_sidebar_subtitle_style())
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        # 2. Navigation Buttons
        self.btn_dash = self._create_nav_btn("Dashboard", 0, True)
        self.btn_lib = self._create_nav_btn("Library", 1)
        self.btn_hist = self._create_nav_btn("History", 3)
        self.btn_sett = self._create_nav_btn("Settings", 4)

        layout.addWidget(self.btn_dash)
        layout.addWidget(self.btn_lib)
        layout.addWidget(self.btn_hist)
        layout.addStretch()

        # 3. Bottom Actions
        self.btn_restart = QPushButton("  Restart App")
        self.btn_restart.setObjectName("SecondaryButton")
        self.btn_restart.setFixedHeight(40)
        self.btn_restart.setCursor(Qt.PointingHandCursor)
        self.btn_restart.clicked.connect(self.restart_requested.emit)
        
        layout.addWidget(self.btn_restart)
        layout.addSpacing(10)
        layout.addWidget(self.btn_sett)

    def _create_nav_btn(self, text, index, active=False):
        btn = QPushButton(f"  {text}")
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
