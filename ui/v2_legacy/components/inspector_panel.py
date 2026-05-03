import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QFrame, QScrollArea, QComboBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from ui.widgets.image_widgets import ImageLoader
from ui.widgets.buttons import PrimaryButton, SecondaryButton, DangerButton
from core.renamer import format_filename
from ui.styles import UIStyles

class InspectorPanel(QWidget):
    """
    Side panel for batch-resolving metadata and managing selections.
    """
    apply_metadata = Signal(list, dict) # [file_paths], metadata_details
    remove_requested = Signal(list)     # [file_paths]
    type_change_requested = Signal(list, str) # [file_paths], new_type
    extra_type_change_requested = Signal(list, str) # [file_paths], new_extra_type
    season_change_requested = Signal(list, str) # [file_paths], season_num
    episode_change_requested = Signal(list, str) # [file_paths], episode_start
    link_parent_requested = Signal(list)       # [file_paths]
    sequence_requested = Signal() # Trigger order wizard

    def __init__(self, parent, pipeline=None):
        super().__init__(parent)
        self.pipeline = pipeline
        self.selected_paths = []
        self.search_results = []
        
        self.setFixedWidth(400)
        self.setObjectName("InspectorPanel")
        self.setStyleSheet(UIStyles.INSPECTOR_PANEL)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)

        # Header
        title_lbl = QLabel("Inspector")
        title_lbl.setObjectName("Title")
        layout.addWidget(title_lbl)

        # Selection Management
        self.selection_header = QHBoxLayout()
        self.summary_lbl = QLabel("0 files selected")
        self.summary_lbl.setStyleSheet("color: #6b7280; font-size: 12px;")
        self.selection_header.addWidget(self.summary_lbl)
        
        self.view_list_btn = SecondaryButton("View List")
        self.view_list_btn.setFixedWidth(80)
        self.view_list_btn.clicked.connect(self.toggle_selection_list)
        self.selection_header.addWidget(self.view_list_btn)
        
        self.deselect_btn = DangerButton("Deselect")
        self.deselect_btn.setFixedWidth(80)
        self.deselect_btn.clicked.connect(self.on_deselect_clicked)
        self.selection_header.addWidget(self.deselect_btn)
        
        layout.addLayout(self.selection_header)

        # Selection List (Hidden by default)
        self.selection_list = QListWidget()
        self.selection_list.setFixedHeight(120)
        self.selection_list.setVisible(False)
        self.selection_list.setStyleSheet("""
            QListWidget {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                font-size: 10px;
                color: #4b5563;
            }
        """)
        layout.addWidget(self.selection_list)

        # Action Tabs / Sections
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(UIStyles.SCROLL_AREA)
        
        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setSpacing(20)
        
        # --- Metadata Search Section ---
        search_section = QWidget()
        s_layout = QVBoxLayout(search_section)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(10)
        
        s_layout.addWidget(QLabel("METADATA RESOLVER", objectName="SubTitle"))
        
        self.tank_btn = PrimaryButton("🎯 Tank Search (Identify)")
        self.tank_btn.setMinimumHeight(45)
        self.tank_btn.setToolTip("Open the hierarchical search to resolve all selected files at once.")
        self.tank_btn.clicked.connect(self.on_open_tank_search)
        s_layout.addWidget(self.tank_btn)
        
        self.container_layout.addWidget(search_section)

        # --- Quick Actions Section ---
        actions_section = QWidget()
        a_layout = QVBoxLayout(actions_section)
        a_layout.setContentsMargins(0, 0, 0, 0)
        
        a_layout.addWidget(QLabel("QUICK ACTIONS", objectName="SubTitle"))
        
        # Type Override
        type_row = QHBoxLayout()
        self.bulk_type_combo = QComboBox()
        self.bulk_type_combo.addItems(["movie", "episode", "extra"])
        type_row.addWidget(self.bulk_type_combo)
        
        apply_type_btn = SecondaryButton("Set Type")
        apply_type_btn.clicked.connect(self.on_bulk_type_clicked)
        type_row.addWidget(apply_type_btn)
        a_layout.addLayout(type_row)

        # Season/Episode Manual
        se_row = QHBoxLayout()
        self.bulk_season_input = QLineEdit()
        self.bulk_season_input.setPlaceholderText("S")
        self.bulk_season_input.setFixedWidth(50)
        se_row.addWidget(self.bulk_season_input)
        
        apply_s_btn = SecondaryButton("Set S")
        apply_s_btn.clicked.connect(self.on_bulk_season_clicked)
        se_row.addWidget(apply_s_btn)
        
        self.bulk_episode_input = QLineEdit()
        self.bulk_episode_input.setPlaceholderText("E")
        self.bulk_episode_input.setFixedWidth(50)
        se_row.addWidget(self.bulk_episode_input)
        
        apply_e_btn = SecondaryButton("Set E")
        apply_e_btn.clicked.connect(self.on_bulk_episode_clicked)
        se_row.addWidget(apply_e_btn)
        a_layout.addLayout(se_row)
        
        self.seq_btn = SecondaryButton("Sequence Order Wizard")
        self.seq_btn.clicked.connect(self.sequence_requested.emit)
        a_layout.addWidget(self.seq_btn)

        # Extras Actions
        self.extras_section = QWidget()
        ex_layout = QVBoxLayout(self.extras_section)
        ex_layout.setContentsMargins(0, 0, 0, 0)
        ex_layout.addWidget(QLabel("EXTRAS MANAGEMENT", objectName="SubTitle"))
        
        ex_type_row = QHBoxLayout()
        self.bulk_extra_type_combo = QComboBox()
        from metadata.classifier import EXTRA_TYPE_MAP
        self.bulk_extra_type_combo.addItems(list(EXTRA_TYPE_MAP.values()))
        ex_type_row.addWidget(self.bulk_extra_type_combo)
        
        apply_ex_type_btn = SecondaryButton("Set Sub-type")
        apply_ex_type_btn.clicked.connect(self.on_bulk_extra_type_clicked)
        ex_type_row.addWidget(apply_ex_type_btn)
        ex_layout.addLayout(ex_type_row)
        
        self.link_parent_btn = SecondaryButton("🔗 Link to Parent...")
        self.link_parent_btn.clicked.connect(self.on_link_parent_clicked)
        ex_layout.addWidget(self.link_parent_btn)
        
        a_layout.addWidget(self.extras_section)

        self.remove_btn = DangerButton("Remove from List")
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.selected_paths))
        a_layout.addWidget(self.remove_btn)
        
        self.container_layout.addWidget(actions_section)
        self.container_layout.addStretch()
        
        self.scroll.setWidget(container)
        layout.addWidget(self.scroll)

    def set_minimal_mode(self, minimal):
        """Show/hide sections based on selection context."""
        # For now, we show everything but could refine this
        pass

    def update_selection(self, paths):
        self.selected_paths = paths
        count = len(paths)
        self.summary_lbl.setText(f"{count} file{'s' if count != 1 else ''} selected")
        
        # Update Selection List (Show filenames)
        self.selection_list.clear()
        for p in paths:
            self.selection_list.addItem(os.path.basename(p))

        # Toggle Extras section
        has_extras = any(self.pipeline.metadata_map.get(p, {}).get('file_type') == 'extra' for p in paths)
        self.extras_section.setVisible(has_extras or count > 1)

        # (Removed old quick search title auto-fill)

    def on_open_tank_search(self):
        if not self.selected_paths: return
        
        # Use first file's meta as context
        path = self.selected_paths[0]
        meta = self.pipeline.metadata_map.get(path)
        if not meta: return
        
        from ui.dialogs.selection_dialog import SelectionDialog
        dialog = SelectionDialog(self.window(), self.pipeline, meta)
        if dialog.exec():
            selected = dialog.selected_item
            if selected:
                self.apply_metadata.emit(self.selected_paths, selected)

    def on_bulk_type_clicked(self):
        new_type = self.bulk_type_combo.currentText()
        self.type_change_requested.emit(self.selected_paths, new_type)

    def on_bulk_extra_type_clicked(self):
        new_extra_type = self.bulk_extra_type_combo.currentText()
        self.extra_type_change_requested.emit(self.selected_paths, new_extra_type)

    def on_bulk_season_clicked(self):
        s = self.bulk_season_input.text()
        if s: self.season_change_requested.emit(self.selected_paths, s)

    def on_bulk_episode_clicked(self):
        e = self.bulk_episode_input.text()
        if e: self.episode_change_requested.emit(self.selected_paths, e)

    def toggle_selection_list(self):
        is_visible = self.selection_list.isVisible()
        self.selection_list.setVisible(not is_visible)
        self.view_list_btn.setText("Hide List" if not is_visible else "View List")

    def on_deselect_clicked(self):
        # We need to tell the main window to clear selection
        # or emit a signal. For now, since we have self.parent()...
        # Better: trigger clear_selection on the window
        if hasattr(self.window(), 'clear_selection'):
            self.window().clear_selection()

    def on_link_parent_clicked(self):
        self.link_parent_requested.emit(self.selected_paths)
