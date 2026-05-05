from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from ui.v3.styles.theme import Theme
from ui.v3.components.discovery_table import DiscoveryTable

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
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {Theme.BORDER}; border-radius: 8px; background: {Theme.SURFACE_DARK}; }}
            QTabBar::tab {{ background: {Theme.SURFACE}; color: {Theme.TEXT_MUTED}; padding: 12px 24px; border: 1px solid {Theme.BORDER}; border-bottom: none; border-radius: 8px 8px 0 0; font-weight: 700; font-size: 13px; margin-right: 4px; }}
            QTabBar::tab:selected {{ background: {Theme.SURFACE_DARK}; color: {Theme.PRIMARY}; border-bottom: 2px solid {Theme.PRIMARY}; }}
            QTabBar::tab:hover {{ background: {Theme.SURFACE_LIGHT}; color: {Theme.TEXT_MAIN}; }}
        """)
        
        self.tables = {
            "review": DiscoveryTable(),
            "movies": DiscoveryTable(),
            "shows": DiscoveryTable()
        }
        
        self.tabs.addTab(self.tables["review"], "📥 Review")
        self.tabs.addTab(self.tables["movies"], "🎬 Movies")
        self.tabs.addTab(self.tables["shows"], "📺 TV Shows")
        
        layout.addWidget(self.tabs)

    def fill_data(self, split_data):
        for key in ["review", "movies", "shows"]:
            if key in split_data:
                self.tables[key].fill_data(split_data[key])
    
    def get_active_table(self):
        idx = self.tabs.currentIndex()
        mapping = {0: "review", 1: "movies", 2: "shows"}
        return self.tables.get(mapping.get(idx))
