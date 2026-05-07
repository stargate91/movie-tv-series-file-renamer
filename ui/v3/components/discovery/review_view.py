from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide6.QtCore import QSize
from ui.v3.styles.theme import Theme
from ui.v3.components.discovery_table import DiscoveryTable
from core.i18n import T

class ReviewView(QWidget):
    """
    Component for the status-based tabs (Review, Movies, Shows, Trash).
    """
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(Theme.get_inner_tab_widget_style())
        self.tabs.setIconSize(QSize(16, 16))
        
        self.tables = {
            "review": DiscoveryTable(),
            "movies": DiscoveryTable(),
            "shows": DiscoveryTable()
        }
        
        self.tabs.addTab(self.tables["review"], 
            Theme.get_icon("package", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.all") or "Pending Review")
        self.tabs.addTab(self.tables["movies"], 
            Theme.get_icon("movie", size=16, color=Theme.TEXT_MUTED), T("common.types.movies") or "Movies")
        self.tabs.addTab(self.tables["shows"], 
            Theme.get_icon("tv", size=16, color=Theme.TEXT_MUTED), T("common.types.tv_shows") or "TV Shows")
        
        layout.addWidget(self.tabs)

    def fill_data(self, split_data):
        for key in ["review", "movies", "shows"]:
            if key in split_data:
                self.tables[key].fill_data(split_data[key])
    
    def get_active_table(self):
        idx = self.tabs.currentIndex()
        mapping = {0: "review", 1: "movies", 2: "shows"}
        return self.tables.get(mapping.get(idx))
