import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFileDialog, QScrollArea, QProgressBar, QFrame)
from PySide6.QtCore import Qt, Signal

# Import our new modules
from ui.styles import QSS
from ui.utils import WorkerThread, QtUIBridge
from ui.components.movie_card import MovieCard
from ui.components.image_widgets import ImageLoader
from ui.dialogs.selection_dialog import SelectionDialog
from ui.dialogs.settings_dialog import SettingsDialog

from core.config_manager import ConfigManager
from core.pipeline import RenamePipeline
from utils.api_client import APIClient

class MainWindow(QMainWindow):
    progress_signal = Signal(int, int, str)

    def __init__(self):
        super().__init__()
        self.cfg = ConfigManager()
        self.pipeline = None
        self.worker = None
        
        self.setWindowTitle("Movie & TV Renamer Pro (Qt Edition)")
        self.resize(1100, 750)
        self.setStyleSheet(QSS)
        self.setAcceptDrops(True)
        
        self.progress_signal.connect(self.handle_progress)
        self.init_ui()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls: return
        
        dropped_files = []
        valid_exts = [ext.strip().lower() for ext in self.cfg.settings.video_extensions.split(",") if ext.strip()]
        
        for url in urls:
            path = os.path.abspath(os.path.normpath(url.toLocalFile()))
            if not os.path.exists(path): continue
            
            if os.path.isdir(path):
                from metadata.collector import get_all_video_files
                found = get_all_video_files(path, self.cfg.settings.vid_size, self.cfg.settings.recursive, valid_exts)
                # Normalize found paths too
                dropped_files.extend([os.path.abspath(os.path.normpath(f)) for f in found])
            else:
                ext = os.path.splitext(path)[1].lower()
                if ext in valid_exts:
                    dropped_files.append(path)

        if dropped_files:
            self.status_lbl.setText(f"Status: Added {len(dropped_files)} new items")
            if not self.pipeline:
                bridge = QtUIBridge(self)
                api = APIClient(self.cfg.settings.omdb_key, self.cfg.settings.tmdb_key, self.cfg.settings.tmdb_bearer_token)
                self.pipeline = RenamePipeline(self.cfg, api, bridge)
            
            # Normalize existing files as well
            current_files = [os.path.abspath(os.path.normpath(f)) for f in self.pipeline.video_files]
            combined = current_files + dropped_files
            self.pipeline.video_files = list(dict.fromkeys(combined))
            self.on_scan_finished()

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
        
        self.download_btn = QPushButton("🌐 Download Metadata")
        self.download_btn.setObjectName("PrimaryBtn")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.start_download)
        side_layout.addWidget(self.download_btn)
        
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        side_layout.addWidget(self.settings_btn)

        self.clear_btn = QPushButton("🗑️ Clear List")
        self.clear_btn.setStyleSheet("color: #f85149; border-color: #f85149;")
        self.clear_btn.clicked.connect(self.clear_all)
        side_layout.addWidget(self.clear_btn)
        
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
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.results_layout = QVBoxLayout(self.scroll_content)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.results_layout.setSpacing(10)
        self.scroll.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll)
        
        status_layout = QHBoxLayout()
        self.status_lbl = QLabel("Status: Ready")
        self.status_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(8)
        self.pbar.setMaximumWidth(300)
        
        status_layout.addWidget(self.status_lbl)
        status_layout.addStretch()
        status_layout.addWidget(self.pbar)
        main_layout.addLayout(status_layout)
        
        layout.addWidget(main_area)
        
        # --- Selection Toolbar (Hidden by default) ---
        self.selection_bar = QFrame()
        self.selection_bar.setObjectName("SelectionBar")
        self.selection_bar.setFixedHeight(70)
        self.selection_bar.setVisible(False)
        self.selection_bar.setStyleSheet("""
            #SelectionBar {
                background-color: #1f2937; border-top: 3px solid #3b82f6; 
                border-radius: 15px 15px 0 0;
            }
            QLabel { color: white; font-weight: bold; font-size: 14px; }
        """)
        
        bar_layout = QHBoxLayout(self.selection_bar)
        bar_layout.setContentsMargins(25, 0, 25, 0)
        self.selection_lbl = QLabel("0 items selected")
        bar_layout.addWidget(self.selection_lbl)
        
        bar_layout.addStretch()
        
        self.bulk_resolve_btn = QPushButton("🪄 Resolve Selected")
        self.bulk_resolve_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_resolve_btn.setStyleSheet("""
            QPushButton { background: #6366f1; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background: #4f46e5; }
        """)
        self.bulk_resolve_btn.clicked.connect(self.bulk_resolve_selected)
        bar_layout.addWidget(self.bulk_resolve_btn)
        
        self.bulk_remove_btn = QPushButton("🗑️ Remove")
        self.bulk_remove_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_remove_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #f85149; border: 1px solid #f85149; padding: 10px 20px; border-radius: 8px; }
            QPushButton:hover { background: #451a1a; }
        """)
        self.bulk_remove_btn.clicked.connect(self.bulk_remove_selected)
        bar_layout.addWidget(self.bulk_remove_btn)
        
        main_layout.addWidget(self.selection_bar)
        
        self.selected_files = set()

    def update_selection(self, file_path, is_selected):
        if is_selected:
            self.selected_files.add(file_path)
        else:
            self.selected_files.discard(file_path)
            
        count = len(self.selected_files)
        self.selection_bar.setVisible(count > 0)
        self.selection_lbl.setText(f"{count} files selected")

    def bulk_remove_selected(self):
        from ui.components.movie_card import MovieCard
        # Find and remove
        for f in list(self.selected_files):
            self.pipeline.remove_file(f)
        self.selected_files.clear()
        self.selection_bar.setVisible(False)
        self.refresh_list()

    def bulk_resolve_selected(self):
        if not self.selected_files: return
        
        # We use the first file's meta as a base for the search
        first_file = list(self.selected_files)[0]
        meta = self.pipeline.metadata_results.get(first_file)
        
        from ui.dialogs.selection_dialog import SelectionDialog
        dialog = SelectionDialog(self, self.pipeline, meta)
        if dialog.exec():
            selected_meta = dialog.selected_item
            if not selected_meta: return
            
            # Sort selected files by name to ensure E01, E02... order
            sorted_files = sorted(list(self.selected_files))
            
            for f_path in sorted_files:
                current_meta = self.pipeline.metadata_results.get(f_path)
                if not current_meta: continue
                
                new_meta = current_meta.copy()
                new_meta['is_manual'] = True
                new_meta['status'] = 'one_match'
                
                from metadata.metadata import classify_result
                classify_result(f_path, [selected_meta], self.pipeline.api, new_meta)
                self.pipeline.metadata_results[f_path] = new_meta
            
            self.selected_files.clear()
            self.selection_bar.setVisible(False)
            self.refresh_list()

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
        self.stat_total.setText("Total Files: 0")
        self.stat_matches.setText("Matched: 0")
        self.download_btn.setEnabled(False)
        self.folder_lbl.setText("Folder: None")
        self.refresh_list()

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
        if not self.pipeline: return
        self.stat_total.setText(f"Total Files: {len(self.pipeline.video_files)}")
        self.download_btn.setEnabled(True)
        self.status_lbl.setText("Status: Scan Complete")
        self.refresh_list()

    def start_download(self):
        self.status_lbl.setText("Status: Downloading Metadata...")
        self.download_btn.setEnabled(False)
        self.worker = WorkerThread(self.pipeline.step_2_extract_metadata)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.start()

    def on_download_finished(self):
        self.status_lbl.setText("Status: Download Complete")
        self.refresh_list()

    def handle_progress(self, current, total, status):
        self.pbar.setMaximum(total)
        self.pbar.setValue(current)
        if status: self.status_lbl.setText(f"Status: {status}")

    def refresh_list(self):
        from ui.components.group_headers import SeriesHeader, SeasonHeader
        self.clear_results()
        if not self.pipeline or not self.pipeline.video_files:
            msg = QLabel("\n\n\n📦\nDrag & Drop Files or Folders Here\n<small>or use the 'Select Folder' button</small>")
            msg.setAlignment(Qt.AlignCenter)
            msg.setStyleSheet("color: #8b949e; font-size: 20px; font-weight: bold;")
            self.results_layout.addWidget(msg)
            return

        # Build normalized lookup for results
        metadata_results = {}
        for r in self.pipeline.collected_results:
            norm_p = os.path.abspath(os.path.normpath(r['file_path']))
            metadata_results[norm_p] = r
        
        def get_rank(vid):
            v_norm = os.path.abspath(os.path.normpath(vid))
            meta = metadata_results.get(v_norm)
            if not meta: return 4
            s = meta.get('status', 'pending')
            is_manual = meta.get('is_manual', False)
            if s == 'multiple_matches': return 0
            if s == 'no_match': return 1
            if is_manual: return 2
            if s == 'one_match': return 3
            if s == 'complex_match': return 5
            return 4
            
        # Grouping
        norm_video_files = [os.path.abspath(os.path.normpath(f)) for f in self.pipeline.video_files]
        by_rank = {0: [], 1: [], 2: [], 3: [], 4: [], 5: []}
        for f in norm_video_files:
            by_rank[get_rank(f)].append(f)

        def remove_item(v):
            if self.pipeline:
                v_norm = os.path.abspath(os.path.normpath(v))
                if v_norm in self.pipeline.video_files:
                    self.pipeline.video_files.remove(v_norm)
                self.pipeline.collected_results = [r for r in self.pipeline.collected_results if os.path.abspath(os.path.normpath(r['file_path'])) != v_norm]
                self.refresh_list()

        matched_count = 0
        for rank in [0, 1, 2, 3, 4, 5]: 
            vids = by_rank[rank]
            if not vids: continue
            
            # Group Header
            header_text = ""
            if rank == 0 or rank == 1: header_text = "⚠️ NEEDS ATTENTION"
            elif rank == 2: header_text = "✨ RESOLVED BY YOU"
            elif rank == 3: header_text = "✅ AUTO-MATCHED"
            elif rank == 4: header_text = "📂 FILES READY FOR DOWNLOAD"
            elif rank == 5: header_text = "🚨 COMPLEX CASES (Manual review required)"
            
            header = QLabel(header_text)
            color = "#f85149" if rank == 5 else "#6b7280"
            header.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 12px; margin-top: 30px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;")
            self.results_layout.addWidget(header)

            # Separate Movies and TV
            movies = []
            series_groups = {} # { "Series Title": { "Season X": [vids] } }
            
            for v in vids:
                meta = metadata_results.get(v)
                details = meta.get('details') if meta else None
                
                if meta and meta['file_type'] == 'episode' and isinstance(details, dict):
                    # It's an episode with valid details, group it
                    s_title = details.get('series_name') or details.get('name') or "Unknown Series"
                    s_num = details.get('season_number', 1)
                    
                    if s_title not in series_groups: 
                        series_groups[s_title] = {"poster": details.get('series_poster_path'), "seasons": {}}
                    if s_num not in series_groups[s_title]["seasons"]: 
                        series_groups[s_title]["seasons"][s_num] = []
                    series_groups[s_title]["seasons"][s_num].append(v)
                else:
                    movies.append(v)

            # Display Movies
            for m in movies:
                card = MovieCard(m, metadata_results.get(m), 
                                 on_edit=lambda _, v=m, meta=metadata_results.get(m): self.open_selection(v, meta),
                                 on_remove=lambda _, v=m: remove_item(v))
                
                # Multi-selection
                card.checkbox.setChecked(m in self.selected_files)
                card.selection_changed.connect(lambda is_sel, path=m: self.update_selection(path, is_sel))
                
                self.results_layout.addWidget(card)
                if rank == 3: matched_count += 1

            # Display Series
            for s_title, s_data in series_groups.items():
                all_series_files = []
                for s_num, episodes in s_data['seasons'].items():
                    all_series_files.extend(episodes)
                
                # Series Header with batch action (disabled for complex cases)
                first_meta = metadata_results.get(all_series_files[0])
                self.results_layout.addWidget(SeriesHeader(
                    s_title, s_data['poster'],
                    on_edit=(lambda _, files=all_series_files, m=first_meta: self.open_batch_selection(files, m)) if rank != 5 else None
                ))
                
                for s_num, episodes in sorted(s_data['seasons'].items()):
                    # Get season info from first episode of this season
                    first_ep_meta = metadata_results.get(episodes[0])
                    s_poster = first_ep_meta['details'].get('season_poster_path') if first_ep_meta else None
                    s_range = first_ep_meta['details'].get('season_year_range', '') if first_ep_meta else ""
                    
                    self.results_layout.addWidget(SeasonHeader(
                        s_num, s_poster, s_range,
                        on_edit=(lambda _, files=episodes, m=first_ep_meta: self.open_batch_selection(files, m)) if rank != 5 else None
                    ))
                    
                    for ep in episodes:
                        card = MovieCard(ep, metadata_results.get(ep),
                                         on_edit=lambda _, v=ep, meta=metadata_results.get(ep): self.open_selection(v, meta),
                                         on_remove=lambda _, v=ep: remove_item(v))
                        
                        # Multi-selection
                        card.checkbox.setChecked(ep in self.selected_files)
                        card.selection_changed.connect(lambda is_sel, path=ep: self.update_selection(path, is_sel))
                        # Add indentation for episodes
                        ep_container = QWidget()
                        ep_layout = QHBoxLayout(ep_container)
                        ep_layout.setContentsMargins(80, 0, 0, 0) # Deeper Indent
                        ep_layout.addWidget(card)
                        self.results_layout.addWidget(ep_container)
                        if rank == 3: matched_count += 1
        
        self.stat_matches.setText(f"Matched: {matched_count}")

    def clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

    def open_batch_selection(self, files, meta):
        dialog = SelectionDialog(self, self.pipeline, meta)
        if dialog.exec():
            selected = dialog.selected_item
            if not selected: return
            
            # Show a simple progress message in console/status
            print(f"Applying batch metadata to {len(files)} files...")
            
            for f_path in files:
                current_meta = self.pipeline.metadata_results.get(f_path)
                if not current_meta: continue
                
                # Update with selected series info
                new_meta = current_meta.copy()
                new_meta['is_manual'] = True
                new_meta['status'] = 'one_match'
                
                # Use metadata standardizer logic to re-classify this file with the new series ID
                from metadata.metadata import classify_result
                classify_result(f_path, [selected], self.pipeline.api, new_meta)
                
                self.pipeline.metadata_results[f_path] = new_meta
            
            self.refresh_list()

    def open_selection(self, file_path, meta):
        if not meta: return
        dialog = SelectionDialog(self, self.pipeline, meta)
        if dialog.exec():
            meta['status'] = 'one_match'
            meta['details'] = dialog.selected_item
            meta['is_manual'] = True
            self.refresh_list()

    def open_settings(self):
        dialog = SettingsDialog(self, self.cfg)
        dialog.exec()

def start_qt_ui():
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
