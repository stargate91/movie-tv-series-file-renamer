from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QStackedLayout
from PySide6.QtCore import QSize
from ui.v3.styles.theme import Theme
from ui.v3.components.discovery_table import DiscoveryTable
from core.i18n import T

class ConflictsView(QWidget):
    """
    Modular component for the Name Clashes tab.
    Shows sub-tabs (Videos / Extras) only when both types are present.
    """
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._has_subtabs = False
        self._init_ui()

    def _init_ui(self):
        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)

        # Mode 1: Single table (no sub-tabs)
        self.table = DiscoveryTable()
        self._stack.addWidget(self.table)

        # Mode 2: Sub-tabbed view
        self._tab_container = QWidget()
        tab_layout = QVBoxLayout(self._tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(Theme.get_inner_tab_widget_style())
        self.tabs.setIconSize(QSize(16, 16))

        self.tables = {
            "video": DiscoveryTable(),
            "extra": DiscoveryTable()
        }

        self.tabs.addTab(self.tables["video"],
            Theme.get_icon("film", size=16, color=Theme.TEXT_MUTED),
            T("discovery.subtabs.videos"))
        self.tabs.addTab(self.tables["extra"],
            Theme.get_icon("paperclip", size=16, color=Theme.TEXT_MUTED),
            T("discovery.subtabs.extras"))

        tab_layout.addWidget(self.tabs)
        self._stack.addWidget(self._tab_container)

    def fill_data(self, data, is_conflicts=True):
        """Split data into videos and extras, show sub-tabs only if both exist."""
        videos = [v for v in data if v.get('category', 'video') == 'video']
        extras = [v for v in data if v.get('category', 'video') != 'video']

        has_both = len(videos) > 0 and len(extras) > 0

        if has_both:
            self._has_subtabs = True
            self._stack.setCurrentIndex(1)
            self.tables["video"].fill_data(videos, is_conflicts=is_conflicts)
            self.tables["extra"].fill_data(extras, is_conflicts=is_conflicts)
        else:
            self._has_subtabs = False
            self._stack.setCurrentIndex(0)
            self.table.fill_data(data, is_conflicts=is_conflicts)

    def get_active_table(self):
        """Returns the currently visible table."""
        if self._has_subtabs:
            idx = self.tabs.currentIndex()
            mapping = {0: "video", 1: "extra"}
            return self.tables.get(mapping.get(idx))
        return self.table

    def apply_filters(self, filter_type, search_text):
        if self._has_subtabs:
            for t in self.tables.values():
                t.apply_filters(filter_type, search_text)
        else:
            self.table.apply_filters(filter_type, search_text)
