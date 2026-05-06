from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme

class ModernDialog(QDialog):
    """
    A custom themed dialog that matches the application's aesthetic.
    Use this instead of standard QMessageBox for a premium feel.
    """
    def __init__(self, title, message, icon_name="alert", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.result_value = False
        self._init_ui(title, message, icon_name)

    def _init_ui(self, title, message, icon_name):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Main Frame
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER};
                border-radius: 12px;
            }}
        """)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(30, 30, 30, 30)
        c_layout.setSpacing(20)

        # Header with Icon
        header_lay = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(Theme.get_pixmap(icon_name, size=32, color=Theme.PRIMARY if icon_name != "alert" else Theme.ERROR))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {Theme.TEXT_MAIN}; border: none; background: transparent;")
        
        header_lay.addWidget(icon_lbl)
        header_lay.addWidget(title_lbl)
        header_lay.addStretch()
        c_layout.addLayout(header_lay)

        # Message Body
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"font-size: 14px; color: {Theme.TEXT_MUTED}; border: none; background: transparent; line-height: 1.4;")
        c_layout.addWidget(msg_lbl)

        # Buttons
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        
        self.btn_no = QPushButton("Cancel")
        self.btn_no.setFixedSize(100, 38)
        self.btn_no.setCursor(Qt.PointingHandCursor)
        self.btn_no.setStyleSheet(Theme.get_secondary_button_style())
        self.btn_no.clicked.connect(self.reject)
        
        self.btn_yes = QPushButton("Confirm")
        self.btn_yes.setFixedSize(120, 38)
        self.btn_yes.setCursor(Qt.PointingHandCursor)
        self.btn_yes.setStyleSheet(Theme.get_primary_button_style() if icon_name != "alert" else Theme.get_danger_button_style())
        self.btn_yes.clicked.connect(self.accept)
        
        btn_lay.addWidget(self.btn_no)
        btn_lay.addWidget(self.btn_yes)
        c_layout.addLayout(btn_lay)

        layout.addWidget(container)

    @staticmethod
    def confirm(parent, title, message, icon="alert"):
        dlg = ModernDialog(title, message, icon, parent)
        return dlg.exec() == QDialog.Accepted

    @staticmethod
    def show_message(parent, title, message, icon="check"):
        dlg = ModernDialog(title, message, icon, parent)
        dlg.btn_no.hide() # Hide cancel button for info messages
        dlg.btn_yes.setText("OK")
        dlg.exec()

from PySide6.QtWidgets import QFrame # Import QFrame for the container
