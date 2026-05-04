import os
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QApplication,
                             QLabel, QFrame, QPushButton, QProgressBar, QMessageBox, QTabWidget)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal, QTimer

from ui.v3.styles.theme import Theme
from ui.v3.components.inspector_panel import InspectorPanel
from ui.v3.components.manual_resolve_dialog import ManualResolveDialog
from ui.v3.components.preview_dialog import PreviewDialog
from ui.v3.components.discovery_table import DiscoveryTable
from ui.v3.components.notification_bar import NotificationBar
from ui.v3.workers.discovery_workers import DataLoader, PosterPrefetcher, RenameWorker, PlanWorker, DropProcessor, UndoWorker

logger = logging.getLogger(__name__)

class DiscoveryPage(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.loader = None
        self.poster_worker = None
        self.active_workers = [] 
        self._init_ui()
        QTimer.singleShot(100, self.refresh_data)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header Row
        header = QHBoxLayout()
        title = QLabel("Discovery Console")
        title.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search files...")
        self.search_box.setFixedWidth(300)
        self.search_box.setStyleSheet(Theme.get_input_style())
        self.search_box.textChanged.connect(self._on_search_changed)

        self.scan_new_btn = QPushButton("Scan Directory")
        self.scan_new_btn.setFixedWidth(140)
        self.scan_new_btn.setStyleSheet(Theme.get_secondary_button_style())

        refresh_btn = QPushButton("Refresh List")
        refresh_btn.setFixedWidth(120)
        refresh_btn.setStyleSheet(Theme.get_secondary_button_style())
        refresh_btn.clicked.connect(self.refresh_data)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.search_box)
        header.addWidget(self.scan_new_btn)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {Theme.BORDER}; border-radius: 8px; background: {Theme.SURFACE_DARK}; }}
            QTabBar::tab {{ background: {Theme.SURFACE}; color: {Theme.TEXT_MUTED}; padding: 12px 24px; border: 1px solid {Theme.BORDER}; border-bottom: none; border-radius: 8px 8px 0 0; font-weight: 700; font-size: 13px; margin-right: 4px; }}
            QTabBar::tab:selected {{ background: {Theme.SURFACE_DARK}; color: {Theme.PRIMARY}; border-bottom: 2px solid {Theme.PRIMARY}; }}
            QTabBar::tab:hover {{ background: {Theme.SURFACE_LIGHT}; color: {Theme.TEXT_MAIN}; }}
        """)
        
        # Create Tables for each tab
        self.tables = {
            "review": DiscoveryTable(),
            "movies": DiscoveryTable(),
            "shows": DiscoveryTable(),
            "extras": DiscoveryTable(),
            "dropped": DiscoveryTable(),
            "trash": DiscoveryTable()
        }

        for key, table in self.tables.items():
            self._setup_table_signals(table)

        self.tabs.addTab(self.tables["review"], "📥 Review")
        self.tabs.addTab(self.tables["movies"], "🎬 Movies")
        self.tabs.addTab(self.tables["shows"], "📺 TV Shows")
        
        # Extras Tab with Sub-filters
        extras_container = QWidget()
        extras_layout = QVBoxLayout(extras_container)
        extras_layout.setContentsMargins(10, 10, 10, 10)
        extras_layout.setSpacing(10)
        
        sub_filter_layout = QHBoxLayout()
        sub_filter_layout.setSpacing(8)
        self.extra_filters = {}
        for label, val in [("All", "all"), ("Bonus Videos", "extra"), ("Images", "image"), ("Metadatas", "metadata"), ("Subtitles", "subtitle")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            if val == "all": btn.setChecked(True)
            btn.setStyleSheet(Theme.get_sub_chip_style())
            btn.clicked.connect(lambda checked=False, v=val: self._on_extra_subfilter_changed(v))
            sub_filter_layout.addWidget(btn)
            self.extra_filters[val] = btn
        sub_filter_layout.addStretch()
        
        extras_layout.addLayout(sub_filter_layout)
        extras_layout.addWidget(self.tables["extras"], 1)
        
        # Dropped Tab (Zsilip)
        self.dropped_container = QWidget()
        dropped_layout = QVBoxLayout(self.dropped_container)
        dropped_layout.setContentsMargins(10, 10, 10, 10)
        dropped_layout.setSpacing(10)
        
        dropped_actions = QHBoxLayout()
        self.import_all_btn = QPushButton("🚀 Import All to Library")
        self.import_all_btn.setStyleSheet(Theme.get_primary_button_style())
        self.import_all_btn.clicked.connect(self._on_import_all)
        
        self.import_sel_btn = QPushButton("📥 Import Selected")
        self.import_sel_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.import_sel_btn.clicked.connect(self._on_import_selected)
        
        self.clear_dropped_btn = QPushButton("🧹 Clear List")
        self.clear_dropped_btn.setStyleSheet(Theme.get_danger_button_style())
        self.clear_dropped_btn.clicked.connect(self._on_clear_dropped)
        
        dropped_actions.addWidget(self.import_all_btn)
        dropped_actions.addWidget(self.import_sel_btn)
        dropped_actions.addStretch()
        dropped_actions.addWidget(self.clear_dropped_btn)
        
        dropped_layout.addLayout(dropped_actions)
        dropped_layout.addWidget(self.tables["dropped"], 1)
        
        self.tabs.addTab(self.tables["review"], "📥 Review")
        self.tabs.addTab(self.tables["movies"], "🎬 Movies")
        self.tabs.addTab(self.tables["shows"], "📺 TV Shows")
        self.tabs.addTab(extras_container, "📎 Extras")
        self.tabs.addTab(self.dropped_container, "📦 Dropped")
        self.tabs.addTab(self.tables["trash"], "🗑️ Trash")
        
        # Main content split
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        content_layout.addWidget(self.tabs, 7)
        
        self.inspector = InspectorPanel()
        content_layout.addWidget(self.inspector, 3)
        layout.addLayout(content_layout)

        # Drop Overlay
        self.drop_overlay = QFrame(self)
        self.drop_overlay.setObjectName("DropOverlay")
        self.drop_overlay.setStyleSheet(f"""
            #DropOverlay {{
                background-color: {Theme.PRIMARY}cc;
                border: 3px dashed white;
                border-radius: 20px;
            }}
        """)
        self.drop_overlay.hide()
        overlay_layout = QVBoxLayout(self.drop_overlay)
        overlay_label = QLabel("🚀 Drop files to Ingest into Library")
        overlay_label.setStyleSheet("color: white; font-size: 24px; font-weight: 800;")
        overlay_label.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(overlay_label)
        
        self.setAcceptDrops(True)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"QProgressBar {{ background: transparent; border: none; }} QProgressBar::chunk {{ background: {Theme.PRIMARY}; }}")
        self.progress_bar.hide()
        
        self.status_info = QLabel("")
        self.status_info.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; font-weight: 600;")
        self.status_info.setAlignment(Qt.AlignCenter)
        self.status_info.hide()
        
        layout.addWidget(self.status_info)
        layout.addWidget(self.progress_bar)

        # Batch Action Bar
        self.batch_bar = QFrame()
        self.batch_bar.setFixedHeight(60)
        self.batch_bar.setStyleSheet(f"background: {Theme.PRIMARY}; border-radius: 12px;")
        bb_layout = QHBoxLayout(self.batch_bar)
        bb_layout.setContentsMargins(20, 0, 20, 0)
        
        self.batch_label = QLabel("0 items selected")
        self.batch_label.setStyleSheet("color: white; font-weight: 700; font-size: 14px; border: none;")
        
        clear_batch_btn = QPushButton("🧹 Clear Match")
        clear_batch_btn.setFixedWidth(130)
        clear_batch_btn.setStyleSheet("background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.4); padding: 8px 12px; font-weight: 700; border-radius: 6px;")
        clear_batch_btn.clicked.connect(self._on_batch_clear)

        bb_layout.addWidget(self.batch_label)
        bb_layout.addStretch()
        bb_layout.addWidget(clear_batch_btn)
        self.batch_bar.hide()
        layout.addWidget(self.batch_bar)

        # Final rename button
        self.apply_btn = QPushButton("Apply Renames")
        self.apply_btn.setFixedHeight(50)
        self.apply_btn.setStyleSheet(Theme.get_primary_button_style())
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        layout.addWidget(self.apply_btn)

        # Notification Bar (Snackbar)
        self.notif_bar = NotificationBar(self)
        self.notif_bar.undo_requested.connect(self._on_undo_requested)

        # Shortcuts
        from PySide6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Ctrl+A"), self).activated.connect(self._on_select_all)
        QShortcut(QKeySequence.Delete, self).activated.connect(self._on_delete_pressed)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.drop_overlay.show()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.drop_overlay.hide()

    def dropEvent(self, event):
        self.drop_overlay.hide()
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        
        if paths:
            self.progress_bar.show()
            self.progress_bar.setRange(0, 0)
            
            # Switch to Dropped tab immediately
            self.tabs.setCurrentIndex(4) # Dropped tab
            
            self.drop_worker = DropProcessor(self.engine, paths)
            self.drop_worker.progress.connect(lambda p, t: self.progress_bar.setValue(p))
            self.drop_worker.finished.connect(self.refresh_data)
            self.drop_worker.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.drop_overlay.setGeometry(self.rect())

    def _on_select_all(self):
        table = self._get_active_table()
        if not table: return
        
        # Select ONLY visible rows
        table.clearSelection()
        for row in range(table.rowCount()):
            if not table.isRowHidden(row):
                table.selectRow(row)

    def _on_delete_pressed(self):
        table = self._get_active_table()
        if not table: return
        selected = table.selectedItems()
        if not selected: return
        
        idx = self.tabs.currentIndex()
        is_dropped_tab = (idx == 4) # 4 is the Dropped tab index
        
        unique_ids = set()
        for item in selected:
            id_item = table.item(item.row(), 1)
            if id_item: unique_ids.add(id_item.data(Qt.UserRole))
            
        if not unique_ids: return
        
        # Confirm for batch action
        action_name = "Remove" if is_dropped_tab else "Ignore"
        if len(unique_ids) > 5:
            res = QMessageBox.question(self, action_name, f"{action_name} {len(unique_ids)} files?")
            if res != QMessageBox.Yes: return

        if is_dropped_tab:
            # Physical delete from DB for dropped items
            with self.engine.db._get_connection() as conn:
                for fid in unique_ids:
                    conn.execute("DELETE FROM media_files WHERE id = ?", (fid,))
                    conn.execute("DELETE FROM file_media_links WHERE file_id = ?", (fid,))
        else:
            # Normal ignore for library items
            for fid in unique_ids:
                f_data = self.engine.db.get_file_by_id(fid)
                if f_data:
                    curr_status = f_data.get('match_status', 'PENDING')
                    self.engine.db.update_file(fid, match_status='IGNORED', previous_match_status=curr_status)
        
        self.refresh_data()

    def _setup_table_signals(self, table):
        table.itemSelectionChanged.connect(self._on_selection_changed)
        table.fix_requested.connect(self._on_fix_requested)
        table.open_folder_requested.connect(self._on_open_folder_requested)
        table.ignore_requested.connect(self._on_ignore_requested)
        table.clear_match_requested.connect(self._on_clear_match_requested)
        table.restore_requested.connect(self._on_restore_requested)

    def refresh_data(self):
        if self.loader and self.loader.isRunning(): return
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        self.loader = DataLoader(self.engine)
        self.loader.data_ready.connect(self._on_data_ready)
        self.loader.start()

    def _on_data_ready(self, videos, poster_paths):
        self.progress_bar.hide()
        
        # Split data by categories
        split_data = {
            "review": [],
            "movies": [],
            "shows": [],
            "extras": [],
            "dropped": [],
            "trash": []
        }
        
        for v in videos:
            status = v.get('match_status', 'pending').upper()
            mtype = v.get('_media_type_from_db') or v.get('fn_media_type')
            cat = v.get('category', 'video')
            is_manual = v.get('is_manual', 0)
            
            if status == 'IGNORED':
                split_data["trash"].append(v)
            elif is_manual:
                split_data["dropped"].append(v)
            elif cat != 'video':
                split_data["extras"].append(v)
            elif status == 'MATCHED':
                if mtype == 'movie':
                    split_data["movies"].append(v)
                else:
                    split_data["shows"].append(v)
            else:
                # PENDING, MULTIPLE, UNCERTAIN, NO_MATCH
                split_data["review"].append(v)
        
        # Fill each table
        for key, data in split_data.items():
            self.tables[key].fill_data(data)
            
        # Prefetch posters
        if poster_paths:
            self.poster_worker = PosterPrefetcher(self.engine, poster_paths)
            self.poster_worker.start()

    def _on_import_all(self):
        """Move all dropped files to the permanent library."""
        with self.engine.db._get_connection() as conn:
            conn.execute("UPDATE media_files SET is_manual = 0 WHERE is_manual = 1")
        self.refresh_data()
        self.tabs.setCurrentIndex(0) # Back to Review

    def _on_import_selected(self):
        """Move only selected dropped files to the permanent library."""
        table = self.tables["dropped"]
        selected = table.selectedItems()
        unique_ids = set(table.item(item.row(), 1).data(Qt.UserRole) for item in selected)
        
        for fid in unique_ids:
            self.engine.db.update_file(fid, is_manual=0)
        
        self.refresh_data()

    def _on_clear_dropped(self):
        """Delete dropped files from the DB (but not from disk)."""
        res = QMessageBox.question(self, "Clear List", "Clear all items from the Dropped list?\n(Files will remain on your computer)")
        if res == QMessageBox.Yes:
            with self.engine.db._get_connection() as conn:
                # 1. Clear candidates for these files
                conn.execute("DELETE FROM match_candidates WHERE file_id IN (SELECT id FROM media_files WHERE is_manual = 1)")
                # 2. Clear links for these files
                conn.execute("DELETE FROM file_media_links WHERE file_id IN (SELECT id FROM media_files WHERE is_manual = 1)")
                # 3. Finally delete the files
                conn.execute("DELETE FROM media_files WHERE is_manual = 1")
                conn.commit()
            self.refresh_data()

    def _on_extra_subfilter_changed(self, val):
        self.tables["extras"].apply_filters(val, self.search_box.text())

    def _on_search_changed(self, text):
        for table in self.tables.values():
            # Note: apply_filters in DiscoveryTable doesn't know about our tab mode,
            # but it will still filter the items IT has.
            # We pass 'all' because the data is already pre-split.
            table.apply_filters("all", text)

    def _get_active_table(self):
        idx = self.tabs.currentIndex()
        mapping = {
            0: "review",
            1: "movies",
            2: "shows",
            3: "extras",
            4: "dropped",
            5: "trash"
        }
        key = mapping.get(idx)
        return self.tables.get(key)

    def _on_selection_changed(self):
        table = self._get_active_table()
        if not table: return
        
        selected = table.selectedItems()
        if not selected:
            self.inspector.set_empty()
            self.batch_bar.hide()
            return

        # Use the first selected row for the inspector
        row = selected[0].row()
        file_id = table.item(row, 1).data(Qt.UserRole)
        file_data = self.engine.db.get_file_by_id(file_id)
        
        if file_data:
            self.inspector.update_tech_info(file_data)
            self.inspector.update_status(file_data.get('match_status', 'pending').upper())
            
            links = self.engine.db.get_links_for_file(file_id)
            if links:
                media = self.engine.db.get_media_item_by_id(links[0]['media_item_id'])
                if media:
                    self.inspector.update_from_data(media)
                    # Load posters
                    self._load_tv_posters(
                        series_path=media.get('poster_path'),
                        season_path=None, # TODO: fetch season if available
                        episode_path=None
                    )
            else:
                self.inspector.title_label.setText(file_data['file_name'])
                self.inspector.poster_carousel.clear()

        # Batch Bar
        unique_rows = set(item.row() for item in selected)
        count = len(unique_rows)
        if count > 1:
            self.batch_label.setText(f"{count} items selected")
            self.batch_bar.show()
        else:
            self.batch_bar.hide()

    def _load_tv_posters(self, series_path=None, season_path=None, episode_path=None):
        pixmaps = []
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        cache_dir = os.path.join(root, 'data', 'cache', 'posters')
        for path in [series_path, season_path, episode_path]:
            if not path:
                pixmaps.append(None)
                continue
            local_path = os.path.join(cache_dir, path.lstrip('/'))
            if os.path.exists(local_path):
                pixmap = QPixmap(local_path)
                pixmaps.append(pixmap if not pixmap.isNull() else None)
            else:
                pixmaps.append(None)
        
        self.inspector.poster_carousel.set_tv_posters(
            series_pix=pixmaps[0],
            season_pix=pixmaps[1],
            episode_pix=pixmaps[2]
        )

    def _on_fix_requested(self, vid):
        dialog = ManualResolveDialog(self.engine, vid)
        if dialog.exec():
            # Refresh specifically this row across all tables (it might move tabs!)
            self.refresh_data() 

    def _on_ignore_requested(self, file_id):
        f_data = self.engine.db.get_file_by_id(file_id)
        if f_data:
            curr_status = f_data.get('match_status', 'PENDING')
            self.engine.db.update_file(file_id, match_status='IGNORED', previous_match_status=curr_status)
        self.refresh_data()

    def _on_restore_requested(self, file_id, row_idx):
        f_data = self.engine.db.get_file_by_id(file_id)
        target_status = 'PENDING'
        if f_data and f_data.get('previous_match_status'):
            target_status = f_data['previous_match_status']
            
        self.engine.db.update_file(file_id, match_status=target_status)
        self.refresh_data()

    def _on_clear_match_requested(self, file_id):
        self.engine.db.update_file(file_id, match_status='PENDING')
        # Also clear links
        with self.engine.db._get_connection() as conn:
            conn.execute("DELETE FROM file_media_links WHERE file_id = ?", (file_id,))
        self.refresh_data()

    def _on_open_folder_requested(self, path):
        import subprocess
        folder = os.path.dirname(path)
        if os.path.exists(folder):
            subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')

    def _on_batch_clear(self):
        table = self._get_active_table()
        selected = table.selectedItems()
        unique_ids = set(table.item(item.row(), 1).data(Qt.UserRole) for item in selected)
        
        for fid in unique_ids:
            self.engine.db.update_file(fid, match_status='PENDING')
            with self.engine.db._get_connection() as conn:
                conn.execute("DELETE FROM file_media_links WHERE file_id = ?", (fid,))
        
        self.refresh_data()

    def _on_apply_clicked(self):
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        
        self.plan_worker = PlanWorker(self.engine)
        self.plan_worker.plan_ready.connect(self._on_plan_ready)
        self.plan_worker.start()

    def _on_plan_ready(self, plan):
        self.progress_bar.hide()
        if not plan:
            QMessageBox.information(self, "Rename", "No files ready for renaming.")
            return
            
        dialog = PreviewDialog(plan)
        if dialog.exec():
            self.progress_bar.show()
            self.status_info.show()
            self.worker = RenameWorker(self.engine, plan)
            self.worker.progress.connect(self._on_worker_progress)
            self.worker.finished.connect(self._on_rename_finished)
            self.worker.start()

    def _on_worker_progress(self, val, text):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(val)
        self.status_info.setText(text)

    def _on_rename_finished(self, results):
        self.progress_bar.hide()
        self.status_info.hide()
        
        if results['success'] > 0:
            msg = f"✅ {results['success']} files renamed successfully."
            self.notif_bar.show_message(msg, batch_id=results.get('batch_id'))
        elif results['failed'] > 0:
            QMessageBox.critical(self, "Error", f"Renaming failed for {results['failed']} files.")
            
        self.refresh_data()

    def _on_undo_requested(self, batch_id):
        self.progress_bar.show()
        self.status_info.show()
        self.progress_bar.setRange(0, 0)
        
        self.undo_worker = UndoWorker(self.engine, batch_id)
        self.undo_worker.progress.connect(self._on_worker_progress)
        self.undo_worker.finished.connect(self._on_undo_finished)
        self.undo_worker.start()

    def _on_undo_finished(self, success, failed, errors):
        self.progress_bar.hide()
        self.status_info.hide()
        if success > 0:
            self.notif_bar.show_message(f"⏪ Restored {success} files to original state.", duration=4000)
        
        if failed > 0:
            QMessageBox.warning(self, "Undo Partial", f"Could not restore {failed} files.\nErrors: {', '.join(errors[:3])}")
            
        self.refresh_data()
