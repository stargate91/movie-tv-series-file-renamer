from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QTabWidget, QStackedLayout
from PySide6.QtCore import Qt, Signal, QSize
from ui.v3.styles.theme import Theme
from ui.v3.components.discovery_table import DiscoveryTable
from core.i18n import T

class DroppedView(QWidget):
    """
    Component for the 'Dropped' tab in Discovery Console.
    Handles staging files before they enter the permanent library.
    Shows sub-tabs (Videos / Extras) only when both types are present.
    """
    refresh_requested = Signal()

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._has_subtabs = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Action Bar
        actions = QHBoxLayout()
        self.import_all_btn = QPushButton(T("discovery.dropped.import_all"))
        self.import_all_btn.setIcon(Theme.get_icon("rocket", size=16, color="#FFFFFF"))
        self.import_all_btn.setStyleSheet(Theme.get_primary_button_style())
        self.import_all_btn.clicked.connect(self._on_import_all)
        
        self.import_sel_btn = QPushButton(T("discovery.dropped.import_selected"))
        self.import_sel_btn.setIcon(Theme.get_icon("check", size=16, color=Theme.TEXT_MAIN))
        self.import_sel_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.import_sel_btn.clicked.connect(self._on_import_selected)
        
        self.clear_btn = QPushButton(T("discovery.dropped.clear_list"))
        self.clear_btn.setIcon(Theme.get_icon("trash-2", size=16, color="#FFFFFF"))
        self.clear_btn.setStyleSheet(Theme.get_danger_button_style())
        self.clear_btn.clicked.connect(self._on_clear_dropped)
        
        actions.addWidget(self.import_all_btn)
        actions.addWidget(self.import_sel_btn)
        actions.addStretch()
        actions.addWidget(self.clear_btn)
        layout.addLayout(actions)
        
        # Stacked content: single table or sub-tabbed
        self._content_stack = QWidget()
        self._stack = QStackedLayout(self._content_stack)
        self._stack.setContentsMargins(0, 0, 0, 0)

        # Mode 1: Single table
        self.table = DiscoveryTable()
        self.table.itemSelectionChanged.connect(self._update_button_states)
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
        for t in self.tables.values():
            t.itemSelectionChanged.connect(self._update_button_states)

        self.tabs.addTab(self.tables["video"],
            Theme.get_icon("film", size=16, color=Theme.TEXT_MUTED),
            T("discovery.subtabs.videos"))
        self.tabs.addTab(self.tables["extra"],
            Theme.get_icon("paperclip", size=16, color=Theme.TEXT_MUTED),
            T("discovery.subtabs.extras"))

        tab_layout.addWidget(self.tabs)
        self._stack.addWidget(self._tab_container)

        layout.addWidget(self._content_stack)
        
        # Initial state
        self._update_button_states()

    def fill_data(self, data):
        """Split data into videos and extras, show sub-tabs only if both exist."""
        videos = [v for v in data if v.get('category', 'video') == 'video']
        extras = [v for v in data if v.get('category', 'video') != 'video']

        has_both = len(videos) > 0 and len(extras) > 0

        if has_both:
            self._has_subtabs = True
            self._stack.setCurrentIndex(1)
            self.tables["video"].fill_data(videos)
            self.tables["extra"].fill_data(extras)
        else:
            self._has_subtabs = False
            self._stack.setCurrentIndex(0)
            self.table.fill_data(data)

        self._update_button_states()

    def get_active_table(self):
        """Returns the currently visible table."""
        if self._has_subtabs:
            idx = self.tabs.currentIndex()
            mapping = {0: "video", 1: "extra"}
            return self.tables.get(mapping.get(idx))
        return self.table

    def _update_button_states(self):
        """Disables buttons if no data or no selection."""
        active = self.get_active_table()
        has_items = active.rowCount() > 0 if active else False
        has_selection = len(active.selectedItems()) > 0 if active else False
        
        self.import_all_btn.setEnabled(has_items)
        self.clear_btn.setEnabled(has_items)
        self.import_sel_btn.setEnabled(has_selection)

    def _on_import_all(self):
        self.engine.db.files.import_all_manual()
        self.refresh_requested.emit()

    def _on_import_selected(self):
        active = self.get_active_table()
        if not active: return
        selected = active.selectedItems()
        unique_ids = set()
        for item in selected:
            row = item.row()
            fid = active.item(row, 1).data(Qt.UserRole)
            if fid: unique_ids.add(fid)
            
        for fid in unique_ids:
            self.engine.db.files.update_file(fid, is_manual=0)
            
        self.refresh_requested.emit()

    def _on_clear_dropped(self):
        res = QMessageBox.question(self, T("discovery.dropped.clear_confirm_title"), T("discovery.dropped.clear_confirm_msg"))
        if res == QMessageBox.Yes:
            self.engine.db.files.delete_manual()
            self.refresh_requested.emit()

    def apply_filters(self, filter_type, search_text):
        if self._has_subtabs:
            for t in self.tables.values():
                t.apply_filters(filter_type, search_text)
        else:
            self.table.apply_filters(filter_type, search_text)
