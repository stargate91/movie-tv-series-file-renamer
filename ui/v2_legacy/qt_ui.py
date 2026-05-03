import os
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFileDialog, QScrollArea, QProgressBar, 
    QFrame, QCheckBox
)
from PySide6.QtCore import Qt, Signal

# Import our new modules
from ui.styles import UIStyles
from ui.controllers.main_controller import MainController
from ui.managers.list_manager import MediaListManager
from ui.managers.task_coordinator import TaskCoordinator
from ui.views.main_window_ui import MainWindowUI
from core.state import AppState
from ui.utils import WorkerThread, QtUIBridge
from ui.components.movie_card import MovieCard
from ui.widgets.group_headers import SeriesHeader, SeasonHeader
from ui.components.inspector_panel import InspectorPanel
from ui.dialogs.selection_dialog import SelectionDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.preview_dialog import PreviewDialog

from core.config_manager import ConfigManager
from core.pipeline import RenamePipeline
from utils.api_client import APIClient
from utils.cache import FileMatchCache

FILE_CACHE = FileMatchCache()

class MainWindow(QMainWindow):
    progress_signal = Signal(int, int, str)

    def __init__(self):
        super().__init__()
        self.cfg = ConfigManager()
        self.state = AppState() # Centralized state
        self.pipeline = None
        
        self.ignore_multi_select_trigger = False
        
        # Managers & UI Setup
        self.ui_setup = MainWindowUI()
        self.list_mgr = None
        self.ctrl = None
        self.tasks = None
        
        # Setup Layout
        self.ui_setup.setup_ui(self)
        
        self.setAcceptDrops(True)
        self.progress_signal.connect(self.handle_progress)
        self.ctrl = None # Init placeholder
        
        
        # Connect AppState signals (Observer Pattern) - Must be after setup_ui
        self.state.selection_changed.connect(lambda _: self.update_selection_ui())
        self.state.list_reset.connect(self.clear_results)
        self.state.status_msg.connect(lambda msg: self.status_lbl.setText(f"Status: {msg}"))
        
        # Initialize Managers
        self.list_mgr = MediaListManager(self, self.state, self.pipeline, self.results_layout, self.scroll)
        self.tasks = TaskCoordinator(self, self.pipeline, self.state)
        
        # Connect Task Signals
        self.tasks.task_started.connect(self._on_task_started)
        self.tasks.task_finished.connect(self._on_task_finished)
        
        # Connect scroll listener once
        self.scroll.verticalScrollBar().valueChanged.connect(self.list_mgr.handle_scroll)

        # Initialize Filter Pills
        self.pills = {}
        self.init_filter_pills()

    def init_filter_pills(self):
        """Creates the filter chips in the header."""
        modes = [
            ('all', "All"),
            ('pending', "Pending"),
            ('review', "Review Required"),
            ('movies', "Movies"),
            ('series', "Series"),
            ('extras', "Extras")
        ]
        
        for mode, label in modes:
            btn = QPushButton(label)
            btn.setObjectName("FilterPill")
            btn.setProperty("mode", mode)
            btn.setProperty("active", "false")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, m=mode: self.on_filter_pill_clicked(m))
            
            self.window().filters_layout.addWidget(btn)
            self.pills[mode] = btn
            
        # Set default
        self.refresh_filter_pills()
        self.on_filter_pill_clicked('all')

    def refresh_filter_pills(self):
        """Updates which pills are visible based on analysis state."""
        # Check if we have any analysis results
        analysis_done = len(self.state.collected_results) > 0 or len(self.state.metadata_map) > 0
        # If all metadata statuses are 'pending' or 'extra', we are still in discovery phase
        if analysis_done:
            has_real_matches = any(m.get('status') not in ['pending', 'extra'] for m in self.state.metadata_map.values())
            if not has_real_matches:
                analysis_done = False

        # Discovery Phase Tabs: All, Pending, Extras
        # Analysis Phase Tabs: All, Needs Review, Movies, Series, Extras
        
        discovery_modes = ['all', 'pending', 'extras']
        analysis_modes = ['all', 'review', 'movies', 'series', 'extras']
        
        visible_modes = analysis_modes if analysis_done else discovery_modes
        
        for mode, btn in self.pills.items():
            btn.setVisible(mode in visible_modes)
            
        # If current active filter is now hidden, reset to 'all'
        active_mode = next((m for m, b in self.pills.items() if b.property("active") == "true"), "all")
        if active_mode not in visible_modes:
            self.on_filter_pill_clicked('all')

    def on_filter_pill_clicked(self, mode):
        """Switches the list filter and updates UI state."""
        for m, btn in self.pills.items():
            is_active = (m == mode)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        if self.list_mgr:
            self.list_mgr.set_filter(mode)

    def update_pill_counts(self, counts):
        """Updates the labels on the filter pills with current counts."""
        labels = {
            'all': "All",
            'pending': "Pending",
            'review': "Needs Review",
            'movies': "Movies",
            'series': "Series",
            'extras': "Extras"
        }
        for mode, btn in self.pills.items():
            count = counts.get(mode, 0)
            btn.setText(f"{labels[mode]}  {count}")
        
        # Also refresh visibility here to ensure sync
        self.refresh_filter_pills()

    # --- Drag & Drop ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        
        dropped_files = []
        valid_exts = [ext.strip().lower() for ext in self.cfg.settings.video_extensions.split(",") if ext.strip()]
        
        for url in urls:
            path = os.path.abspath(os.path.normpath(url.toLocalFile()))
            if not os.path.exists(path):
                continue
            
            if os.path.isdir(path):
                from metadata.collector import get_all_video_files
                found = get_all_video_files(path, self.cfg.settings.vid_size, self.cfg.settings.recursive, valid_exts)
                dropped_files.extend([os.path.abspath(os.path.normpath(f)) for f in found])
            else:
                ext = os.path.splitext(path)[1].lower()
                if ext in valid_exts:
                    dropped_files.append(path)

        if dropped_files:
            if not self.pipeline:
                bridge = QtUIBridge(self)
                api = APIClient(self.cfg.settings.omdb_key, self.cfg.settings.tmdb_key, self.cfg.settings.tmdb_bearer_token)
                self.pipeline = RenamePipeline(self.cfg, api, bridge, self.state)
            self.ctrl = MainController(self, self.pipeline, self.state)
            self.tasks.pipeline = self.pipeline # Update task pipeline
            self.list_mgr.pipeline = self.pipeline
            self.inspector.pipeline = self.pipeline
            
            current_files = [os.path.abspath(os.path.normpath(f)) for f in self.state.video_files]
            combined = current_files + dropped_files
            self.state.video_files = list(dict.fromkeys(combined))
            self.on_scan_finished()

    # --- Scanning & Processing ---
    def open_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder", self.cfg.settings.folder_path)
        if path:
            self.cfg.settings.folder_path = path
            self.cfg.save()
            self.folder_lbl.setText(f"Folder: {path}")
            self.start_scan()

    def clear_all(self):
        self.state.reset_state() # This will emit list_reset and clear memory
        self.pipeline = None
        self.clear_results() # Clears UI items
        
        self.unified_btn.setEnabled(False)
        self.rename_btn.setEnabled(False)
        self.status_lbl.setText("Status: Ready")
        self.stat_total.setText("Total Files: 0")
        self.stat_matches.setText("Matched: 0")
        self.folder_lbl.setText("Folder: None")
        self.display_items = []
        self.clear_selection()
        self.refresh_filter_pills()


    def start_scan(self):
        self.clear_results()
        self.inspector.set_minimal_mode(True)
        if self.tasks:
            self.tasks.start_scan()

    def on_scan_finished(self):
        self.stat_total.setText(f"Total Files: {len(self.state.video_files)}")
        self.refresh_filter_pills()
        self.refresh_list()
        self.unified_btn.setEnabled(len(self.state.video_files) > 0)
        self.rename_btn.setEnabled(len(self.state.video_files) > 0)
        
        if self.pipeline:
            self.inspector.pipeline = self.pipeline
            self.inspector.set_minimal_mode(True)
            self.status_lbl.setText("Status: Scan Complete. Ready for Analysis.")

    def on_start_unified_analysis(self):
        self.start_unified_analysis()

    def on_unified_analysis_finished(self):
        self.status_lbl.setText("Status: Analysis Complete!")
        self.unified_btn.setEnabled(True)
        self.inspector.set_minimal_mode(False)
        
        has_matches = any(isinstance(r, dict) and r.get('status') == 'one_match' for r in self.pipeline.collected_results)
        self.rename_btn.setEnabled(has_matches)
        self.refresh_filter_pills()
        self.refresh_list()

    def start_unified_analysis(self):
        if not self.pipeline:
            from utils.api_client import APIClient
            from ui.utils import QtUIBridge
            from core.pipeline import RenamePipeline
            from ui.controllers.main_controller import MainController
            
            bridge = QtUIBridge(self)
            api = APIClient(self.cfg.settings.omdb_key, self.cfg.settings.tmdb_key, self.cfg.settings.tmdb_bearer_token)
            self.pipeline = RenamePipeline(self.cfg, api, bridge, self.state)
            self.ctrl = MainController(self, self.pipeline, self.state)
            self.tasks.pipeline = self.pipeline
            self.list_mgr.pipeline = self.pipeline
            self.inspector.pipeline = self.pipeline
            
        self.tasks.start_unified_analysis()

    def start_renaming(self):

        # --- Safety Check: Deletions ---
        if self.pipeline.s.extra_action == "delete":
            to_delete = [p for p, m in self.state.metadata_map.items() if m.get('file_type') == 'extra']
            if to_delete:
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self, 'Confirm Deletion',
                    f"Warning: {len(to_delete)} extra files are marked for DELETION based on your settings.\n\nAre you sure you want to proceed?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

        self.status_lbl.setText("Status: Preparing files for renaming...")
        self.tasks.start_renaming()

    def on_rename_finished(self):
        is_live = self.cfg.settings.live_run
        
        dialog = PreviewDialog(self, self.pipeline.renamed_files)
        dialog.exec()
        
        has_errors = any(t.status == "error" for t in self.pipeline.renamed_files)

        if has_errors:
            self.status_lbl.setText("Status: Rename Aborted! Please resolve collisions.")
            self.status_lbl.setStyleSheet("color: #f85149; font-weight: bold;")
        else:
            mode_str = "RENAMED" if is_live else "PREVIEW"
            self.status_lbl.setText(f"Status: {mode_str} Complete!")
            self.status_lbl.setStyleSheet("color: #3fb950; font-weight: bold;")

        if is_live and not has_errors:
            self.clear_all()
        else:
            self.rename_btn.setEnabled(True)
            self.unified_btn.setEnabled(True)
            self.refresh_list()

    def handle_progress(self, current, total, status):
        # Setting maximum to 0 triggers indeterminate mode. 
        # Setting it back to a positive value stops it.
        self.pbar.setMaximum(total)
        self.pbar.setValue(current)
        if status:
            self.status_lbl.setText(f"Status: {status}")

    def toggle_live_mode(self, state):
        self.cfg.settings.live_run = (state == Qt.Checked.value)
        self.cfg.save()
        color = "#f85149" if self.cfg.settings.live_run else "#8b949e"
        self.live_mode_cb.setStyleSheet(f"color: {color}; font-weight: bold;")

    def refresh_list(self):
        if self.list_mgr:
            self.list_mgr.refresh()

    def clear_results(self):
        if self.list_mgr:
            self.list_mgr.clear_results()

    # --- Item Actions ---
    # --- (End of Item Actions - Delegated to Controller) ---

    def update_selection(self, file_path, is_selected):
        if is_selected:
            self.state.add_selection(file_path)
        else:
            self.state.remove_selection(file_path)

    def clear_selection(self):
        self.state.clear_selection()
        from ui.components.movie_card import MovieCard
        for i in range(self.results_layout.count()):
            item = self.results_layout.itemAt(i)
            if not item: continue
            w = item.widget()
            if not w: continue
            if isinstance(w, MovieCard):
                card = w
            else:
                card = w.findChild(MovieCard)
            if card:
                card.checkbox.setChecked(False)
                card.set_active(False)
        self.state.is_multi_select_mode = False
        self.ignore_multi_select_trigger = False
        self.update_selection_ui()

    def filter_list(self, text):
        if self.list_mgr:
            self.list_mgr.apply_search_filter(text)

    def toggle_sidebar(self):
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed
        target_width = 70 if self.is_sidebar_collapsed else 240
        
        # Update sidebar width
        self.sidebar.setFixedWidth(target_width)
        
        # Toggle Labels
        self.brand_full.setVisible(not self.is_sidebar_collapsed)
        self.tagline_lbl.setVisible(not self.is_sidebar_collapsed)
        self.stat_total.setVisible(not self.is_sidebar_collapsed)
        self.stat_matches.setVisible(not self.is_sidebar_collapsed)
        
        # Toggle Button Texts
        for btn in self.side_btns:
            if self.is_sidebar_collapsed:
                btn.setText(btn.property("icon_only"))
            else:
                btn.setText(btn.property("full_text"))
        
        # Update Toggle Button text/icon if needed
        self.toggle_sidebar_btn.setText("≡" if not self.is_sidebar_collapsed else "»")

    def update_selection_ui(self):
        from ui.components.movie_card import MovieCard
        for i in range(self.results_layout.count()):
            item = self.results_layout.itemAt(i)
            if not item: continue
            w = item.widget()
            if not w: continue
            if isinstance(w, MovieCard):
                card = w
            else:
                card = w.findChild(MovieCard)
            if card:
                is_selected = card.file_path in self.state.selected_files
                
                # In multi-select mode, sync the checkbox state
                if self.state.is_multi_select_mode:
                    self.ignore_multi_select_trigger = True
                    card.checkbox.setChecked(is_selected)
                    self.ignore_multi_select_trigger = False
                    card.set_active(False) # No blue border in multi-select
                else:
                    # In single-select mode, show blue border for the selected item, but NO checkbox
                    card.set_active(is_selected)
                    self.ignore_multi_select_trigger = True
                    card.checkbox.setChecked(False)
                    self.ignore_multi_select_trigger = False
                
        selected_count = len(self.state.selected_files)
        self.inspector.update_selection(list(self.state.selected_files))
        self.inspector.setVisible(selected_count > 0)

    def set_card_checkbox_visually(self, file_path, checked):
        from ui.components.movie_card import MovieCard
        for i in range(self.results_layout.count()):
            item = self.results_layout.itemAt(i)
            if not item: continue
            w = item.widget()
            if not w: continue
            if isinstance(w, MovieCard):
                card = w
            else:
                card = w.findChild(MovieCard)
            if card and card.file_path == file_path:
                card.checkbox.setChecked(checked)
                break

    def select_files_for_inspector(self, file_paths, title=None, season=None):
        """Programmatically select files and open the inspector panel with pre-filled data."""
        # Clear previous selection properly
        self.clear_selection()
        
        # Select all provided files
        for f in file_paths:
            self.state.selected_files.add(f)
            
        # If we selected multiple files (e.g. a whole season), we should be in multi-select mode
        if len(file_paths) > 1:
            self.state.is_multi_select_mode = True
            # In multi-select mode, we DO want to see the checkboxes
            self.ignore_multi_select_trigger = True
            from ui.components.movie_card import MovieCard
            for i in range(self.results_layout.count()):
                item = self.results_layout.itemAt(i)
                if not item: continue
                w = item.widget()
                if not w: continue
                if isinstance(w, MovieCard): card = w
                else: card = w.findChild(MovieCard)
                if card:
                    card.checkbox.setChecked(card.file_path in self.state.selected_files)
            self.ignore_multi_select_trigger = False
        else:
            # Single-select items are just highlighted with set_active via update_selection_ui
            self.state.is_multi_select_mode = False
        
        self.update_selection_ui()
        
        # Pre-fill search with title
        if title and title not in ['Unknown Series', 'Unknown Collection']:
            self.inspector.search_input.setText(title)
            self.inspector.type_combo.setCurrentText("TV Show")
            self.inspector.perform_search()
        
        # Pre-fill season override
        if season is not None:
            self.inspector.season_input.setText(str(season))

    # --- (End of Refactored Section - Delegated to Controller) ---

    # --- (End of Refactored Section - Delegated to Controller) ---
    
    def open_selection(self, file_path, meta):
        # Allow toggling even if meta is None (e.g. freshly scanned files)
        
        # Only handle body clicks if we are already in multi-select mode
        if self.state.is_multi_select_mode:
            # In multi-select mode, clicking the card body just toggles the checkbox
            is_currently_selected = file_path in self.state.selected_files
            self.set_card_checkbox_visually(file_path, not is_currently_selected)
            return
        
        # In normal state, a single click on the card body does nothing.
        # This prevents accidental inspector openings.
        # Users must use the checkbox to enter selection mode, or double-click for quick edit.
        pass

    def open_single_edit_popup(self, file_path, meta):
        # Disable single-edit popup in multi-select mode
        if self.state.is_multi_select_mode:
            return
            
        if not meta: return
        from ui.dialogs.selection_dialog import SelectionDialog
        dialog = SelectionDialog(self, self.pipeline, meta)
        if dialog.exec():
            res = dialog.selected_item
            if not res: return
            
            # Use controller for consistent multi-episode logic if possible, 
            # or handle it here to match existing direct-to-state logic
            if isinstance(res, list):
                # Multi-Episode Selection
                sorted_items = sorted(res, key=lambda x: x.get('episode_number', 0))
                merged_title = " & ".join([item.get('name', 'Unknown') for item in sorted_items])
                merged_nums = [item.get('episode_number') for item in sorted_items]
                
                primary = sorted_items[0]
                details = primary.copy()
                details['name'] = merged_title
                details['episode_number'] = merged_nums
                details['episode_title'] = merged_title
                # Ensure series info is kept
                details['series_title'] = primary.get('series_name') or primary.get('series_title')
                
                meta['file_type'] = 'episode'
                meta['status'] = 'one_match'
                meta['details'] = details
            elif res.get('file_type') == 'extra':
                meta['file_type'] = 'extra'
                meta['extra_type'] = res.get('extra_type')
                meta['status'] = 'extra'
                meta['details'] = {}
            else:
                meta['file_type'] = 'movie' if dialog.type_combo.currentText() == "Movie" else "episode"
                meta['status'] = 'one_match'
                meta['details'] = res
            
            meta['is_manual'] = True
            self.state.metadata_map[file_path] = meta # Use self.state instead of self.pipeline.metadata_map for consistency
            FILE_CACHE.set_match(file_path, meta)
            self.refresh_list()
            self.trigger_background_enrichment([meta])

    def trigger_background_enrichment(self, items_to_enrich):
        if self.tasks:
            self.tasks.trigger_enrichment(items_to_enrich)

    def on_enrichment_finished(self):
        self.refresh_list()
        self.status_lbl.setText("Status: Enrichment Complete!")

    def _on_task_started(self, task_id):
        self.rename_btn.setEnabled(False)
        self.unified_btn.setEnabled(False)
        if task_id == 'scan':
            self.status_lbl.setText("Status: Scanning directory...")
        elif task_id == 'unified_analysis':
            self.status_lbl.setText("Status: Deep Analyzing & Matching (API)...")
        elif task_id == 'renaming':
            self.status_lbl.setText("Status: Renaming files...")
        elif task_id == 'enrichment':
            self.status_lbl.setText("Status: Enriching metadata...")

    def _on_task_finished(self, task_id):
        self.unified_btn.setEnabled(True)
        # Rename button enabled logic is usually handled in specific finish handlers
        if task_id == 'renaming':
             self.status_lbl.setText("Status: Rename Complete!")
        elif task_id == 'unified_analysis':
             self.status_lbl.setText("Status: Analysis Complete!")

    def open_settings(self):
        dialog = SettingsDialog(self, self.cfg)
        dialog.exec()
    def on_clear_cache(self):
        from utils.cache import DataStore
        from PySide6.QtWidgets import QMessageBox
        DataStore.clear_transient_data()
        QMessageBox.information(self, "Cache Cleared", "Metadata, search results, and posters have been cleared. Your settings are preserved.")
        self.clear_all()

def start_qt_ui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
