from PySide6.QtWidgets import QWidget, QVBoxLayout
from ui.v3.components.discovery_table import DiscoveryTable

class ConflictsView(QWidget):
    """
    Modular component for the Name Clashes tab.
    """
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = DiscoveryTable()
        layout.addWidget(self.table)

    def fill_data(self, data, is_conflicts=True):
        self.table.fill_data(data, is_conflicts=is_conflicts)

    def apply_filters(self, filter_type, search_text):
        self.table.apply_filters(filter_type, search_text)
