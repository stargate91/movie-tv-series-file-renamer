import os
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFileDialog, QScrollArea, QProgressBar, 
    QFrame, QCheckBox
)
from PySide6.QtCore import Qt, Signal

# Import our new modules
from ui.styles import QSS
from ui.utils import WorkerThread, QtUIBridge
from ui.components.movie_card import MovieCard
from ui.components.group_headers import SeriesHeader, SeasonHeader
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
        self.pipeline = None
        self.worker = None
        self.selected_files = set()
        self.is_multi_select_mode = False
        self.ignore_multi_select_trigger = False
        
        # Virtual List State
        self.display_items = []  # Flat list of (type, data, extra) tasks
        self.current_loaded_index = 0
        self.chunk_size = 25
        
        self.setWindowTitle("Movie & TV Renamer Pro (Qt Edition)")
        self.resize(1100, 750)
        self.setStyleSheet(QSS)
        self.setAcceptDrops(True)
        
        self.progress_signal.connect(self.handle_progress)
        self.init_ui()
        
        # Connect scroll listener once
        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll_changed)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Sidebar ---
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(20, 30, 20, 30)
        side_layout.setSpacing(15)
        
        title = QLabel("Auto Renamer")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0078d4; margin-bottom: 20px;")
        side_layout.addWidget(title)
        
        self.browse_btn = QPushButton("📁 Select Folder")
        self.browse_btn.clicked.connect(self.browse_and_scan)
        side_layout.addWidget(self.browse_btn)
        
        self.unified_btn = QPushButton("🔍 Analyze & Match")
        self.unified_btn.setObjectName("PrimaryBtn")
        self.unified_btn.setEnabled(False)
        self.unified_btn.clicked.connect(self.on_start_unified_analysis)
        side_layout.addWidget(self.unified_btn)
        
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        side_layout.addWidget(self.settings_btn)

        self.clear_btn = QPushButton("🗑️ Clear List")
        self.clear_btn.setStyleSheet("color: #f85149; border-color: #f85149;")
        self.clear_btn.clicked.connect(self.clear_all)
        side_layout.addWidget(self.clear_btn)

        side_layout.addSpacing(20)

        self.live_mode_cb = QCheckBox("🔥 Live Mode (Real Rename)")
        self.live_mode_cb.setStyleSheet("color: #8b949e; font-weight: bold;")
        self.live_mode_cb.setChecked(self.cfg.settings.live_run)
        self.live_mode_cb.stateChanged.connect(self.toggle_live_mode)
        side_layout.addWidget(self.live_mode_cb)
        
        self.rename_btn = QPushButton("🚀 Start Renaming")
        self.rename_btn.setObjectName("PrimaryBtn")
        self.rename_btn.setStyleSheet("background-color: #3fb950; color: white;")
        self.rename_btn.setEnabled(False)
        self.rename_btn.clicked.connect(self.start_renaming)
        side_layout.addWidget(self.rename_btn)
        
        self.clear_cache_btn = QPushButton("Clear Cache")
        self.clear_cache_btn.setFixedHeight(35)
        self.clear_cache_btn.setCursor(Qt.PointingHandCursor)
        self.clear_cache_btn.setStyleSheet("""
            QPushButton { 
                background: #374151; color: #d1d5db; border: none; 
                border-radius: 6px; font-size: 11px; margin-top: 10px;
            }
            QPushButton:hover { background: #4b5563; color: white; }
        """)
        self.clear_cache_btn.clicked.connect(self.on_clear_cache)
        side_layout.addWidget(self.clear_cache_btn)
        
        side_layout.addStretch()
        
        self.stat_total = QLabel("Total Files: 0")
        self.stat_matches = QLabel("Matched: 0")
        side_layout.addWidget(self.stat_total)
        side_layout.addWidget(self.stat_matches)
        
        layout.addWidget(sidebar)
        
        # --- Main Area ---
        main_area = QWidget()
        main_area.setObjectName("MainArea")
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        self.folder_lbl = QLabel(f"Folder: {self.cfg.settings.folder_path}")
        self.folder_lbl.setStyleSheet("color: #8b949e; font-style: italic;")
        main_layout.addWidget(self.folder_lbl)

        # Top Progress Section (Full Width)
        self.status_lbl = QLabel("Status: Ready")
        self.status_lbl.setStyleSheet("color: #8b949e; font-size: 11px; margin-top: 5px;")
        main_layout.addWidget(self.status_lbl)

        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(6)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet("""
            QProgressBar {
                background-color: #f3f4f6;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.pbar)
        main_layout.addSpacing(10)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.results_layout = QVBoxLayout(self.scroll_content)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.results_layout.setSpacing(10)
        self.scroll.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll)
        
        layout.addWidget(main_area)
        
        # --- Inspector Panel (Right) ---
        self.inspector = InspectorPanel(self, None)
        self.inspector.setVisible(False)
        self.inspector.remove_requested.connect(self.bulk_remove_selected)
        self.inspector.apply_metadata.connect(self.bulk_resolve_selected)
        self.inspector.type_change_requested.connect(self.bulk_change_type)
        self.inspector.season_change_requested.connect(self.bulk_change_season)
        self.inspector.episode_change_requested.connect(self.bulk_change_episode)
        self.inspector.sequence_requested.connect(self.open_sequence_wizard)
        self.inspector.clear_btn.clicked.connect(self.clear_selection)
        layout.addWidget(self.inspector)

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
                self.pipeline = RenamePipeline(self.cfg, api, bridge)
            
            current_files = [os.path.abspath(os.path.normpath(f)) for f in self.pipeline.video_files]
            combined = current_files + dropped_files
            self.pipeline.video_files = list(dict.fromkeys(combined))
            self.on_scan_finished()

    # --- Scanning & Processing ---
    def browse_and_scan(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder", self.cfg.settings.folder_path)
        if path:
            self.cfg.settings.folder_path = path
            self.cfg.save()
            self.folder_lbl.setText(f"Folder: {path}")
            self.start_scan()

    def clear_all(self):
        self.pipeline = None
        self.clear_results()
        self.unified_btn.setEnabled(False)
        self.rename_btn.setEnabled(False)
        self.status_lbl.setText("Status: Ready")
        self.stat_total.setText("Total Files: 0")
        self.folder_lbl.setText("Folder: None")
        self.display_items = []
        self.clear_selection()


    def start_scan(self):
        self.status_lbl.setText("Status: Scanning...")
        self.clear_results()
        self.pipeline = None
        
        def run_logic():
            bridge = QtUIBridge(self)
            api = APIClient(self.cfg.settings.omdb_key, self.cfg.settings.tmdb_key, self.cfg.settings.tmdb_bearer_token)
            self.pipeline = RenamePipeline(self.cfg, api, bridge)
            self.pipeline.step_1_collect_files()

        self.worker = WorkerThread(run_logic)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.start()

    def on_scan_finished(self):
        if not self.pipeline:
            return
        self.stat_total.setText(f"Total Files: {len(self.pipeline.video_files)}")
        self.unified_btn.setEnabled(True)
        self.status_lbl.setText("Status: Scan Complete. Ready for Analysis.")
        self.inspector.pipeline = self.pipeline # Connect pipeline to inspector
        self.refresh_list()

    def on_start_unified_analysis(self):
        self.status_lbl.setText("Status: Deep Analyzing & Matching (NFO/MediaInfo/API)...")
        self.unified_btn.setEnabled(False)
        self.rename_btn.setEnabled(False)
        
        self.worker = WorkerThread(self.pipeline.unified_analysis)
        self.worker.finished.connect(self.on_unified_analysis_finished)
        self.worker.start()

    def on_unified_analysis_finished(self):
        self.status_lbl.setText("Status: Analysis Complete!")
        self.unified_btn.setEnabled(True)
        
        has_matches = any(isinstance(r, dict) and r.get('status') == 'one_match' for r in self.pipeline.collected_results)
        self.rename_btn.setEnabled(has_matches)
        self.refresh_list()

    def start_renaming(self):
        self.status_lbl.setText("Status: Preparing files for renaming...")
        self.rename_btn.setEnabled(False)
        self.unified_btn.setEnabled(False)
        
        def run_rename_logic():
            self.pipeline.step_5_rename()

        self.worker = WorkerThread(run_rename_logic)
        self.worker.finished.connect(self.on_rename_finished)
        self.worker.start()

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
        self.pbar.setMaximum(total)
        self.pbar.setValue(current)
        if status:
            self.status_lbl.setText(f"Status: {status}")

    def toggle_live_mode(self, state):
        self.cfg.settings.live_run = (state == Qt.Checked.value)
        self.cfg.save()
        color = "#f85149" if self.cfg.settings.live_run else "#8b949e"
        self.live_mode_cb.setStyleSheet(f"color: {color}; font-weight: bold;")

    # --- Grouped Lazy Loading ---
    def refresh_list(self):
        """Builds a display task list and starts lazy loading."""
        self.clear_results()
        if not self.pipeline or not self.pipeline.video_files:
            msg = QLabel("\n\n\n📦\nDrag & Drop Files or Folders Here\n<small>or use the 'Select Folder' button</small>")
            msg.setAlignment(Qt.AlignCenter)
            msg.setStyleSheet("color: #8b949e; font-size: 20px; font-weight: bold;")
            self.results_layout.addWidget(msg)
            return

        # 1. Ranking Logic
        def get_rank(vid_path):
            norm_p = os.path.abspath(os.path.normpath(vid_path))
            meta = self.pipeline.metadata_map.get(norm_p)
            if not meta:
                return 4
            status = meta.get('status', 'pending')
            is_manual = meta.get('is_manual', False)
            
            if status == 'multiple_matches': return 0
            if status == 'no_match': return 1
            if is_manual: return 2
            if status == 'one_match': return 3
            if status == 'complex_match': return 5
            return 4

        # 2. Group Files
        norm_files = [os.path.abspath(os.path.normpath(f)) for f in self.pipeline.video_files]
        by_rank = {i: [] for i in range(6)}
        for f in norm_files:
            by_rank[get_rank(f)].append(f)

        # 3. Create Display Item Tasks
        self.display_items = []
        matched_count = 0

        for rank in [0, 1, 2, 3, 4, 5]:
            vids = by_rank[rank]
            if not vids:
                continue

            # Section Header Task
            header_text = {
                0: "⚠️ NEEDS ATTENTION",
                1: "⚠️ NEEDS ATTENTION",
                2: "✨ RESOLVED BY YOU",
                3: "✅ AUTO-MATCHED",
                4: "📂 FILES READY FOR DOWNLOAD",
                5: "🚨 COMPLEX CASES (Manual review required)"
            }[rank]
            self.display_items.append(('header', header_text, rank == 5))

            movies = []
            series_groups = {}
            for v in vids:
                meta = self.pipeline.metadata_map.get(v)
                if not isinstance(meta, dict): meta = {}
                det = meta.get('details') if meta else {}
                if not isinstance(det, dict): det = {}
                
                is_ep = meta and (meta.get('file_type') == 'episode' or meta.get('extras', {}).get('season') is not None)
                
                if is_ep:
                    # For non-matches or multi-matches, group under "Unknown Series" to avoid UI clutter
                    status = meta.get('status')
                    extras = meta.get('extras', {})
                    
                    if status == 'one_match':
                        name = det.get('series_title') or det.get('series_name') or det.get('name') or extras.get('title') or "Unknown Series"
                    else:
                        name = "Unknown Series"
                        
                    sn = det.get('season_number') or extras.get('season') or 1
                    
                    if name not in series_groups:
                        # Prevent misleading posters for generic "Unknown" groups
                        is_generic = name in ["Unknown Series", "Unknown Collection", "Unknown Saga"]
                        poster = (det.get('series_poster_path') or det.get('poster_path')) if not is_generic else None
                        series_groups[name] = {"poster": poster, "seasons": {}}
                    if sn not in series_groups[name]["seasons"]:
                        series_groups[name]["seasons"][sn] = []
                    series_groups[name]["seasons"][sn].append(v)
                else:
                    movies.append(v)

            # Add Movie Tasks
            for m in movies:
                self.display_items.append(('card', m, False))
                if rank == 3: matched_count += 1

            # Add Series Tasks
            for s_title, s_data in series_groups.items():
                all_files = [f for sn in s_data['seasons'] for f in s_data['seasons'][sn]]
                self.display_items.append(('series_header', (s_title, s_data['poster'], all_files, rank == 5), False))
                
                for sn in sorted(s_data['seasons'].keys()):
                    eps = s_data['seasons'][sn]
                    meta = self.pipeline.metadata_map.get(eps[0])
                    det = meta.get('details') if meta and isinstance(meta.get('details'), dict) else {}
                    s_poster = det.get('season_poster_path')
                    s_range = det.get('season_year_range', '')
                    self.display_items.append(('season_header', (sn, s_poster, s_range, eps, rank == 5), False))
                    
                    for ep in eps:
                        self.display_items.append(('card', ep, True)) # True = indented
                        if rank == 3: matched_count += 1

        self.stat_matches.setText(f"Matched: {matched_count}")
        self.current_loaded_index = 0
        self.load_next_chunk()

    def on_scroll_changed(self, value):
        bar = self.scroll.verticalScrollBar()
        if value > bar.maximum() - 250:
            self.load_next_chunk()

    def load_next_chunk(self):
        if not self.pipeline:
            return
        if self.current_loaded_index >= len(self.display_items):
            return
            
        end_idx = min(self.current_loaded_index + self.chunk_size, len(self.display_items))
        
        for i in range(self.current_loaded_index, end_idx):
            item_type, data, extra = self.display_items[i]
            
            if item_type == 'header':
                header = QLabel(data)
                color = "#f85149" if extra else "#6b7280"
                header.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 11px; margin-top: 30px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;")
                self.results_layout.addWidget(header)
                
            elif item_type == 'series_header':
                s_title, poster, files, is_complex = data
                header = SeriesHeader(
                    s_title, poster,
                    on_edit=(lambda _, f=files, t=s_title: self.select_files_for_inspector(f, t)) if not is_complex else None
                )
                self.results_layout.addWidget(header)
                
            elif item_type == 'season_header':
                sn, poster, year_range, eps, is_complex = data
                header = SeasonHeader(
                    sn, poster, year_range,
                    on_edit=(lambda _, f=eps, s=sn: self.select_files_for_inspector(f, season=s)) if not is_complex else None
                )
                self.results_layout.addWidget(header)
                
            elif item_type == 'card':
                file_path = data
                meta = self.pipeline.metadata_map.get(file_path)
                card = MovieCard(
                    file_path, meta,
                    on_click=lambda _, p=file_path, m=meta: self.open_selection(p, m),
                    on_edit=lambda _, p=file_path, m=meta: self.open_single_edit_popup(p, m),
                    on_remove=lambda _, p=file_path: self.remove_file(p)
                )
                card.selection_changed.connect(lambda s, p=file_path: self.update_selection(p, s))
                if file_path in self.selected_files:
                    if self.is_multi_select_mode:
                        card.checkbox.setChecked(True)
                    else:
                        card.set_active(True)
                
                if extra: # Indented for episodes
                    container = QWidget()
                    inner_layout = QHBoxLayout(container)
                    inner_layout.setContentsMargins(60, 0, 0, 0)
                    inner_layout.addWidget(card)
                    self.results_layout.addWidget(container)
                else:
                    self.results_layout.addWidget(card)
                    
        self.current_loaded_index = end_idx

    def clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        try:
            # We don't disconnect here because we only connect once in __init__
            pass
        except:
            pass

    # --- Item Actions ---
    def remove_file(self, file_path):
        if not self.pipeline:
            return
        v_norm = os.path.abspath(os.path.normpath(file_path))
        self.pipeline.video_files = [f for f in self.pipeline.video_files if os.path.abspath(os.path.normpath(f)) != v_norm]
        self.pipeline.collected_results = [r for r in self.pipeline.collected_results if isinstance(r, dict) and os.path.abspath(os.path.normpath(r.get('file_path', ''))) != v_norm]
        if v_norm in self.pipeline.metadata_map:
            del self.pipeline.metadata_map[v_norm]
        self.refresh_list()

    def update_selection(self, file_path, is_selected):
        if is_selected:
            self.selected_files.add(file_path)
            if not getattr(self, 'ignore_multi_select_trigger', False):
                self.is_multi_select_mode = True
        else:
            self.selected_files.discard(file_path)
            if not self.selected_files:
                self.is_multi_select_mode = False
        self.update_selection_ui()

    def clear_selection(self):
        self.ignore_multi_select_trigger = True
        self.selected_files.clear()
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
        self.is_multi_select_mode = False
        self.ignore_multi_select_trigger = False
        self.update_selection_ui()

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
                is_selected = card.file_path in self.selected_files
                
                # In multi-select mode, sync the checkbox state
                if self.is_multi_select_mode:
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
                
        self.inspector.update_selection(list(self.selected_files))

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
            self.selected_files.add(f)
            
        # If we selected multiple files (e.g. a whole season), we should be in multi-select mode
        if len(file_paths) > 1:
            self.is_multi_select_mode = True
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
                    card.checkbox.setChecked(card.file_path in self.selected_files)
            self.ignore_multi_select_trigger = False
        else:
            # Single-select items are just highlighted with set_active via update_selection_ui
            self.is_multi_select_mode = False
        
        self.update_selection_ui()
        
        # Pre-fill search with title
        if title and title not in ['Unknown Series', 'Unknown Collection']:
            self.inspector.search_input.setText(title)
            self.inspector.type_combo.setCurrentText("TV Show")
            self.inspector.perform_search()
        
        # Pre-fill season override
        if season is not None:
            self.inspector.season_input.setText(str(season))

    def bulk_remove_selected(self, paths=None):
        targets = paths if paths else list(self.selected_files)
        for f in targets:
            self.remove_file(f)
        self.clear_selection()

    def bulk_resolve_selected(self, paths, selected):
        if not selected: return
        
        ready_to_enrich = []
        for f_path in sorted(list(paths)):
            current_meta = self.pipeline.metadata_map.get(f_path)
            if not current_meta: continue
            
            new_meta = current_meta.copy()
            new_meta.update({'is_manual': True, 'status': 'one_match'})
            
            # Apply Season Override if present
            s_override = selected.get('season_override')
            if s_override:
                try: new_meta['season_file'] = int(s_override)
                except: pass

            from metadata.metadata import classify_result
            classify_result({'results': [selected], 'total_results': 1}, new_meta, [], self.pipeline.api)
            self.pipeline.metadata_map[f_path] = new_meta
            ready_to_enrich.append(new_meta)
        
        self.clear_selection()
        self.refresh_list()
        self.trigger_background_enrichment(ready_to_enrich)

    def bulk_change_type(self, paths, new_type):
        for f in paths:
            meta = self.pipeline.metadata_map.get(f)
            if meta and isinstance(meta, dict):
                meta['file_type'] = new_type
                meta['status'] = 'no_match' # Reset match status since type changed
                meta['details'] = None
        self.clear_selection()
        self.refresh_list()

    def bulk_change_season(self, paths, new_season):
        ready_to_enrich = []
        for f in paths:
            meta = self.pipeline.metadata_map.get(f)
            if meta and isinstance(meta, dict):
                try:
                    meta['season_file'] = int(new_season)
                    if meta.get('status') == 'one_match':
                        ready_to_enrich.append(meta)
                except ValueError:
                    pass
        self.clear_selection()
        self.refresh_list()
        if ready_to_enrich:
            self.trigger_background_enrichment(ready_to_enrich)

    def bulk_change_episode(self, paths, new_episode):
        try:
            num = int(new_episode)
        except ValueError:
            return
            
        ready_to_enrich = []
        for f in paths:
            meta = self.pipeline.metadata_map.get(f)
            if meta and isinstance(meta, dict):
                meta['episode_file'] = num
                if meta.get('status') == 'one_match':
                    ready_to_enrich.append(meta)
        
        self.clear_selection()
        self.refresh_list()
        if ready_to_enrich:
            self.trigger_background_enrichment(ready_to_enrich)

    def open_sequence_wizard(self):
        paths = list(self.selected_files)
        if len(paths) < 2: return
        
        from ui.dialogs.episode_order_dialog import EpisodeOrderDialog
        from PySide6.QtWidgets import QDialog
        
        dialog = EpisodeOrderDialog(self, paths, default_start=1)
        if dialog.exec() == QDialog.Accepted:
            ordered_paths, start_num = dialog.get_results()
        else:
            return # Cancelled
            
        ready_to_enrich = []
        for i, f in enumerate(ordered_paths):
            meta = self.pipeline.metadata_map.get(f)
            if meta and isinstance(meta, dict):
                meta['episode_file'] = start_num + i
                if meta.get('status') == 'one_match':
                    ready_to_enrich.append(meta)
        
        self.clear_selection()
        self.refresh_list()
        if ready_to_enrich:
            self.trigger_background_enrichment(ready_to_enrich)

    def open_selection(self, file_path, meta):
        if not meta: return
        
        # Only handle body clicks if we are already in multi-select mode
        if getattr(self, 'is_multi_select_mode', False):
            # In multi-select mode, clicking the card body just toggles the checkbox
            is_currently_selected = file_path in self.selected_files
            self.set_card_checkbox_visually(file_path, not is_currently_selected)
            return
        
        # In normal state, a single click on the card body does nothing.
        # This prevents accidental inspector openings.
        # Users must use the checkbox to enter selection mode, or double-click for quick edit.
        pass

    def open_single_edit_popup(self, file_path, meta):
        # Disable single-edit popup in multi-select mode
        if getattr(self, 'is_multi_select_mode', False):
            return
            
        if not meta: return
        from ui.dialogs.selection_dialog import SelectionDialog
        dialog = SelectionDialog(self, self.pipeline, meta)
        if dialog.exec():
            meta['status'] = 'one_match'
            meta['details'] = dialog.selected_item
            meta['is_manual'] = True
            self.pipeline.metadata_map[file_path] = meta
            FILE_CACHE.set_match(file_path, meta)
            self.refresh_list()
            self.trigger_background_enrichment([meta])

    def trigger_background_enrichment(self, items_to_enrich):
        def run_enrich():
            self.pipeline.handled_results = items_to_enrich
            self.pipeline.step_4_standardize_and_enrich()
            
        self.worker = WorkerThread(run_enrich)
        self.worker.finished.connect(self.on_enrichment_finished)
        self.worker.start()

    def on_enrichment_finished(self):
        self.status_lbl.setText("Status: Enrichment Complete!")
        self.refresh_list()

    def open_settings(self):
        dialog = SettingsDialog(self, self.cfg)
        dialog.exec()
    def on_clear_cache(self):
        from utils.cache import DataStore
        from PySide6.QtWidgets import QMessageBox
        DataStore.wipe_all_data()
        QMessageBox.information(self, "Total Cache Wiped", "All metadata, search results, and images have been cleared.")
        self.refresh_list()

def start_qt_ui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
