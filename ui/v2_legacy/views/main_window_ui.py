import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QFrame, QScrollArea, QProgressBar, QCheckBox
)
from PySide6.QtCore import Qt
from ui.styles import UIStyles
from ui.components.inspector_panel import InspectorPanel

class MainWindowUI:
    """
    Handles the structural layout and widget creation for the main window.
    Decouples the 'Look' from the 'Logic'.
    """
    def setup_ui(self, window):
        window.setWindowTitle("RENDA - Intelligent Media Renamer")
        window.resize(1250, 800)
        window.setStyleSheet(UIStyles.MAIN_WINDOW + UIStyles.SIDEBAR + UIStyles.SIDEBAR_BUTTON)

        central = QWidget()
        window.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar (Left Column) ---
        window.sidebar = QWidget()
        window.sidebar.setObjectName("Sidebar")
        window.sidebar.setFixedWidth(240)
        window.is_sidebar_collapsed = False
        side_layout = QVBoxLayout(window.sidebar)
        side_layout.setContentsMargins(10, 20, 10, 20)
        side_layout.setSpacing(10)
        
        # Logo / Toggle Area
        logo_layout = QHBoxLayout()
        window.logo_lbl = QLabel("R")
        window.logo_lbl.setObjectName("SidebarLogo")
        window.logo_lbl.setAlignment(Qt.AlignCenter)
        window.logo_lbl.setFixedSize(40, 40)
        window.logo_lbl.setStyleSheet("""
            background: #6366f1; color: white; border-radius: 8px; 
            font-weight: 900; font-size: 24px;
        """)
        logo_layout.addWidget(window.logo_lbl)
        
        window.brand_full = QLabel("RENDA")
        window.brand_full.setObjectName("SidebarTitle")
        logo_layout.addWidget(window.brand_full)
        
        logo_layout.addStretch()
        
        window.toggle_sidebar_btn = QPushButton("≡")
        window.toggle_sidebar_btn.setObjectName("SidebarToggle")
        window.toggle_sidebar_btn.setFixedSize(30, 30)
        window.toggle_sidebar_btn.setCursor(Qt.PointingHandCursor)
        window.toggle_sidebar_btn.clicked.connect(window.toggle_sidebar)
        logo_layout.addWidget(window.toggle_sidebar_btn)
        
        side_layout.addLayout(logo_layout)

        window.tagline_lbl = QLabel("Intelligent Media Renamer")
        window.tagline_lbl.setObjectName("SidebarTagline")
        window.tagline_lbl.setWordWrap(True)
        side_layout.addWidget(window.tagline_lbl)

        side_layout.addSpacing(20)

        # Actions Section - Store original texts for toggling
        window.side_btns = []
        
        def create_side_btn(icon, text, action=None, connect_to=None):
            btn = QPushButton(f"{icon}  {text}")
            btn.setObjectName("SidebarBtn")
            btn.setProperty("full_text", f"{icon}  {text}")
            btn.setProperty("icon_only", icon)
            btn.setCursor(Qt.PointingHandCursor)
            if action: btn.setProperty("action", action)
            if connect_to: btn.clicked.connect(connect_to)
            side_layout.addWidget(btn)
            window.side_btns.append(btn)
            return btn

        window.select_btn = create_side_btn("📁", "Select Folder", connect_to=window.open_folder_dialog)
        window.unified_btn = create_side_btn("🔍", "Unified Analysis", "primary", window.on_start_unified_analysis)
        window.unified_btn.setEnabled(False)
        window.rename_btn = create_side_btn("🚀", "Rename Files", "success", window.start_renaming)
        window.rename_btn.setEnabled(False)
        
        side_layout.addSpacing(20)
        
        window.clear_all_btn = create_side_btn("🧹", "Clear List", "danger", window.clear_all)

        side_layout.addStretch()

        # Bottom Stats in Sidebar
        window.stat_total = QLabel("Total Files: 0")
        window.stat_total.setObjectName("StatLabel")
        side_layout.addWidget(window.stat_total)

        window.stat_matches = QLabel("Matched: 0")
        window.stat_matches.setObjectName("StatLabel")
        window.stat_matches.setStyleSheet("color: #10b981;")
        side_layout.addWidget(window.stat_matches)

        window.settings_btn = create_side_btn("⚙", "Settings", connect_to=window.open_settings)

        main_layout.addWidget(window.sidebar)

        # --- Separator 1 ---
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setFrameShadow(QFrame.Plain)
        sep1.setFixedWidth(1)
        sep1.setStyleSheet("background-color: #cbd5e1; border: none;")
        main_layout.addWidget(sep1)

        # --- Main Area (Middle Column) ---
        main_area = QWidget()
        main_area.setObjectName("MainArea")
        main_area_layout = QVBoxLayout(main_area)
        main_area_layout.setContentsMargins(30, 30, 30, 20)
        main_area_layout.setSpacing(15)

        # Header
        header = QHBoxLayout()
        window.folder_lbl = QLabel("Folder: None")
        window.folder_lbl.setStyleSheet("font-weight: bold; color: #374151; font-size: 14px;")
        header.addWidget(window.folder_lbl)
        header.addStretch()
        
        window.live_mode_cb = QCheckBox("LIVE RUN")
        window.live_mode_cb.setToolTip("If unchecked, files will not be renamed (Preview Mode)")
        window.live_mode_cb.stateChanged.connect(window.toggle_live_mode)
        header.addWidget(window.live_mode_cb)
        main_area_layout.addLayout(header)

        # --- Filter Pills Row ---
        window.filters_layout = QHBoxLayout()
        window.filters_layout.setSpacing(8)
        window.filters_layout.setAlignment(Qt.AlignLeft)
        
        # We'll create the actual buttons in the controller/window to handle logic easily
        main_area_layout.addLayout(window.filters_layout)

        # Search Bar
        window.search_input = QLineEdit()
        window.search_input.setPlaceholderText("🔍 Filter files by name or recognized title...")
        window.search_input.setStyleSheet("""
            QLineEdit { 
                background: white; border: 1px solid #cbd5e1; border-radius: 8px; 
                padding: 10px 15px; font-size: 14px; color: #1e293b;
            }
            QLineEdit:focus { border-color: #6366f1; border-width: 2px; }
        """)
        window.search_input.textChanged.connect(window.filter_list)
        main_area_layout.addWidget(window.search_input)

        # Scroll Area
        window.scroll = QScrollArea()
        window.scroll.setWidgetResizable(True)
        window.scroll.setStyleSheet(UIStyles.SCROLL_AREA)
        
        container = QWidget()
        window.results_layout = QVBoxLayout(container)
        window.results_layout.setAlignment(Qt.AlignTop)
        window.results_layout.setSpacing(10)
        window.results_layout.setContentsMargins(0, 0, 10, 0)
        window.scroll.setWidget(container)
        main_area_layout.addWidget(window.scroll)

        # Bottom Progress Section
        window.pbar = QProgressBar()
        window.pbar.setFixedHeight(6)
        window.pbar.setTextVisible(False)
        window.pbar.setStyleSheet(UIStyles.PROGRESS_BAR)
        main_area_layout.addWidget(window.pbar)

        window.status_lbl = QLabel("Status: Ready")
        window.status_lbl.setStyleSheet("color: #6b7280; font-size: 11px;")
        main_area_layout.addWidget(window.status_lbl)

        main_layout.addWidget(main_area, 1)

        # --- Separator 2 ---
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setFrameShadow(QFrame.Plain)
        sep2.setFixedWidth(1)
        sep2.setStyleSheet("background-color: #cbd5e1; border: none;")
        main_layout.addWidget(sep2)

        # --- Inspector Column (Right Column) ---
        window.inspector = InspectorPanel(window, window.pipeline)
        window.inspector.setVisible(False)
        
        # Connect Inspector Signals
        window.inspector.apply_metadata.connect(lambda p, m: window.ctrl.bulk_resolve_selected(p, m))
        window.inspector.remove_requested.connect(lambda p: window.ctrl.bulk_remove_selected(p))
        window.inspector.type_change_requested.connect(lambda p, t: window.ctrl.bulk_change_type(p, t))
        window.inspector.extra_type_change_requested.connect(lambda p, et: window.ctrl.bulk_change_extra_type(p, et))
        window.inspector.season_change_requested.connect(lambda p, s: window.ctrl.bulk_change_season(p, s))
        window.inspector.episode_change_requested.connect(lambda p, e: window.ctrl.bulk_change_episode(p, e))
        window.inspector.link_parent_requested.connect(lambda p: window.ctrl.manual_link_parent(p))
        window.inspector.sequence_requested.connect(lambda: window.ctrl.open_sequence_wizard(list(window.state.selected_files)))
        
        main_layout.addWidget(window.inspector)
