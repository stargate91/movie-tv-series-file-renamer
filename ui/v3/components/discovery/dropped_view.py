from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal
from ui.v3.styles.theme import Theme
from ui.v3.components.discovery_table import DiscoveryTable
from core.i18n import T

class DroppedView(QWidget):
    """
    Component for the 'Dropped' tab in Discovery Console.
    Handles staging files before they enter the permanent library.
    """
    refresh_requested = Signal()

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
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
        
        # Table
        self.table = DiscoveryTable()
        self.table.itemSelectionChanged.connect(self._update_button_states)
        layout.addWidget(self.table)
        
        # Initial state
        self._update_button_states()

    def fill_data(self, data):
        self.table.fill_data(data)
        self._update_button_states()

    def _update_button_states(self):
        """Disables buttons if no data or no selection."""
        has_items = self.table.rowCount() > 0
        has_selection = len(self.table.selectedItems()) > 0
        
        self.import_all_btn.setEnabled(has_items)
        self.clear_btn.setEnabled(has_items)
        self.import_sel_btn.setEnabled(has_selection)

    def _on_import_all(self):
        self.engine.db.files.import_all_manual()
        self.refresh_requested.emit()

    def _on_import_selected(self):
        selected = self.table.selectedItems()
        # Collect unique file IDs from row data
        unique_ids = set()
        for item in selected:
            row = item.row()
            fid = self.table.item(row, 1).data(Qt.UserRole)
            if fid: unique_ids.add(fid)
            
        for fid in unique_ids:
            self.engine.db.files.update_file(fid, is_manual=0)
            
        self.refresh_requested.emit()

    def _on_clear_dropped(self):
        res = QMessageBox.question(self, T("discovery.dropped.clear_confirm_title"), T("discovery.dropped.clear_confirm_msg"))
        if res == QMessageBox.Yes:
            self.engine.db.files.delete_manual()
            self.refresh_requested.emit()
