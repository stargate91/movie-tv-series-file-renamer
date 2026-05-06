from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget
from PySide6.QtCore import Signal
from ui.v3.styles.theme import Theme
from core.i18n import T

class BasketWidget(QWidget):
    clear_requested = Signal()
    confirm_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setVisible(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header = QHBoxLayout()
        header.addWidget(QLabel(T("manual_resolve.basket")))
        self.clear_btn = QPushButton(T("manual_resolve.clear"))
        self.clear_btn.setObjectName("SecondaryButton")
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        header.addWidget(self.clear_btn)
        layout.addLayout(header)
        
        self.list = QListWidget()
        layout.addWidget(self.list)
        
        self.confirm_btn = QPushButton(T("manual_resolve.confirm_all"))
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setFixedHeight(45)
        self.confirm_btn.setStyleSheet(Theme.get_success_button_style())
        self.confirm_btn.clicked.connect(self.confirm_requested.emit)
        layout.addWidget(self.confirm_btn)

    def refresh(self, basket):
        self.list.clear()
        for item in basket:
            m = item['media']
            label = f"{m['title']}"
            if m['media_type'] in ('tv', 'season', 'episode'):
                label += f" [S{str(item['s']).zfill(2)}E{str(item['e']).zfill(2)}]"
            self.list.addItem(label)
        self.confirm_btn.setEnabled(len(basket) > 0)
