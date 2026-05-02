from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

class PrimaryButton(QPushButton):
    """A prominent blue button for main actions."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("ActionBtn")
        self.setCursor(Qt.PointingHandCursor)

class SecondaryButton(QPushButton):
    """A white button with border for secondary actions."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("SecondaryBtn")
        self.setCursor(Qt.PointingHandCursor)

class DangerButton(QPushButton):
    """A button with red text for destructive actions (e.g. Remove)."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("SecondaryBtn") # Uses secondary base style
        self.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.setCursor(Qt.PointingHandCursor)
