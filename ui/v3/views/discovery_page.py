import os
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QApplication,
                             QLabel, QFrame, QPushButton, QProgressBar, QMessageBox, QTabWidget, QFileDialog, QMenu)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal, QTimer, QSize

from ui.v3.styles.theme import Theme
from ui.v3.components.discovery_table import DiscoveryTable
from ui.v3.components.inspector_panel import InspectorPanel
from ui.v3.components.edit_file_dialog import EditFileDialog
from ui.v3.components.batch_operations_dialog import BatchOperationsDialog
from ui.v3.components.batch_resolve_dialog import BatchResolveDialog
from ui.v3.components.manual_resolve_dialog import ManualResolveDialog
from ui.v3.components.preview_dialog import PreviewDialog
from ui.v3.components.notification_bar import NotificationBar
from ui.v3.workers.discovery_workers import DataLoader, PosterPrefetcher, RenameWorker, PlanWorker, DropProcessor, UndoWorker, SyncWorker
from core.i18n import T

# Modular Views
from ui.v3.components.discovery.review_view import ReviewView
from ui.v3.components.discovery.dropped_view import DroppedView
from ui.v3.components.discovery.extras_view import ExtrasView
from ui.v3.components.discovery.conflicts_view import ConflictsView
from ui.v3.components.discovery.trash_view import TrashView

logger = logging.getLogger(__name__)

class DiscoveryPage(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.loader = None
        self.poster_worker = None
        self.sync_worker = None
        self.worker = None
        self.plan_worker = None
        self.undo_worker = None
        self.active_workers = [] 
        self.last_batch_id = None
        self._init_ui()
        QTimer.singleShot(100, self.refresh_data)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 1. Header
        header = QHBoxLayout()
        title = QLabel(T("discovery.title"))
        title.setStyleSheet(Theme.get_page_header_style())
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(T("discovery.search_placeholder"))
        self.search_box.setFixedWidth(300)
        self.search_box.setStyleSheet(Theme.get_input_style())
        self.search_box.textChanged.connect(self._on_search_changed)

        self.scan_new_btn = QPushButton(T('discovery.actions.scan_new'))
        self.scan_new_btn.setIcon(Theme.get_icon("search", size=16, color=Theme.TEXT_MAIN))
        self.scan_new_btn.setFixedWidth(140)
        self.scan_new_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.scan_new_btn.clicked.connect(self._on_manual_scan_triggered)

        refresh_btn = QPushButton(T("discovery.actions.refresh"))
        refresh_btn.setIcon(Theme.get_icon("refresh", size=16, color=Theme.TEXT_MAIN))
        refresh_btn.setFixedWidth(140)
        refresh_btn.setStyleSheet(Theme.get_secondary_button_style())
        refresh_btn.clicked.connect(self.refresh_data)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.search_box)
        header.addWidget(self.scan_new_btn)
        self.refresh_btn = refresh_btn
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        # 2. Main Tabs (Modular)
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet(Theme.get_tab_widget_style())

        self.review_view = ReviewView(self.engine)
        self.conflicts_view = ConflictsView(self.engine)
        self.extras_view = ExtrasView(self.engine)
        self.dropped_view = DroppedView(self.engine)
        self.trash_view = TrashView(self.engine)

        self.main_tabs.setIconSize(QSize(16, 16))
        self.main_tabs.addTab(self.review_view, Theme.get_icon("search", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.library"))
        self.main_tabs.addTab(self.conflicts_view, Theme.get_icon("alert-triangle", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.conflicts"))
        self.main_tabs.addTab(self.extras_view, Theme.get_icon("paperclip", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.extras"))
        self.main_tabs.addTab(self.dropped_view, Theme.get_icon("package", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.dropped"))
        self.main_tabs.addTab(self.trash_view, Theme.get_icon("trash-2", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.trash"))

        # Connect internal signals
        self.dropped_view.refresh_requested.connect(self.refresh_data)
        for view in [self.review_view, self.conflicts_view, self.extras_view, self.dropped_view, self.trash_view]:
            # Wire table signals to main page handlers
            if isinstance(view, DiscoveryTable):
                self._setup_table_signals(view)
            elif hasattr(view, 'tables'):
                for table in view.tables.values(): self._setup_table_signals(table)
            elif hasattr(view, 'table'): self._setup_table_signals(view.table)

        # 3. Content Layout (Tabs + Inspector)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        content_layout.addWidget(self.main_tabs, 7)
        
        self.inspector = InspectorPanel()
        self.inspector.set_preferred_language(self.engine.config.settings.metadata_language)
        content_layout.addWidget(self.inspector, 3)
        layout.addLayout(content_layout)

        # 4. Progress & Batch Bars
        self._init_status_elements(layout)

        # 5. Apply Button
        self.apply_btn = QPushButton(T("discovery.actions.apply"))
        self.apply_btn.setFixedHeight(50)
        self.apply_btn.setStyleSheet(Theme.get_primary_button_style())
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        layout.addWidget(self.apply_btn)

        # Notification & Overlays
        self.notif_bar = NotificationBar(self)
        self.notif_bar.undo_requested.connect(self._on_undo_requested)
        self.notif_bar.action_requested.connect(self._on_custom_action_requested)
        self._init_drop_overlay()

    def _init_status_elements(self, layout):
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setStyleSheet(Theme.get_progress_bar_detailed_style())
        self.progress_bar.hide()
        
        self.status_info = QLabel("")
        self.status_info.setStyleSheet(Theme.get_status_label_style())
        self.status_info.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_info.hide()
        
        # Abort Button (styled more subtly, placed away from the center)
        self.abort_btn = QPushButton(T("discovery.buttons.abort"))
        self.abort_btn.setObjectName("abort-btn")
        self.abort_btn.setCursor(Qt.PointingHandCursor)
        self.abort_btn.setMinimumWidth(80)
        self.abort_btn.setFixedHeight(24)
        self.abort_btn.setStyleSheet("""
            QPushButton#abort-btn {
                background: transparent;
                border: 1px solid #ef4444;
                color: #ef4444;
                border-radius: 4px;
                padding: 2px 12px;
                font-weight: 600;
                font-size: 11px;
                text-transform: uppercase;
            }
            QPushButton#abort-btn:hover {
                background: #ef4444;
                color: white;
            }
            QPushButton#abort-btn:pressed {
                background: #b91c1c;
            }
        """)
        self.abort_btn.clicked.connect(self._on_abort_clicked)
        self.abort_btn.hide()

        # Status & Abort Row
        status_row = QHBoxLayout()
        status_row.addWidget(self.status_info)
        status_row.addStretch()
        status_row.addWidget(self.abort_btn)
        
        # Progress Container
        self.progress_container = QWidget()
        self.progress_container.hide()
        p_layout = QVBoxLayout(self.progress_container)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.setSpacing(8)
        
        p_layout.addLayout(status_row)
        p_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_container)

        self.batch_bar = QFrame()
        self.batch_bar.setFixedHeight(60)
        self.batch_bar.setStyleSheet(Theme.get_batch_bar_style())
        bb_layout = QHBoxLayout(self.batch_bar)
        bb_layout.setContentsMargins(20, 0, 20, 0)
        self.batch_label = QLabel(T("discovery.messages.items_selected", count=0))
        self.batch_label.setStyleSheet(Theme.get_batch_label_style())
        self.batch_action_btn = QPushButton(T('discovery.actions.batch_actions'))
        self.batch_action_btn.setIcon(Theme.get_icon("edit-3", size=16, color=Theme.TEXT_MAIN))
        self.batch_action_btn.setStyleSheet(Theme.get_batch_button_style('primary'))
        self.batch_action_btn.clicked.connect(self._on_batch_actions_requested)
        self.batch_identify_btn = QPushButton(T("discovery.batch.identify"))
        self.batch_identify_btn.setIcon(Theme.get_icon("wand-2", size=16, color=Theme.TEXT_MAIN))
        self.batch_identify_btn.setStyleSheet(Theme.get_batch_button_style('identify'))
        self.batch_identify_btn.clicked.connect(self._on_batch_identify_requested)

        self.batch_restore_btn = QPushButton(T("discovery.actions.restore"))
        self.batch_restore_btn.setIcon(Theme.get_icon("check", size=16, color=Theme.TEXT_MAIN))
        self.batch_restore_btn.setStyleSheet(Theme.get_batch_button_style('success'))
        self.batch_restore_btn.clicked.connect(self._on_batch_restore_requested)
        self.batch_restore_btn.hide()

        # 3. Overflow Menu for Destructive Actions
        self.batch_more_btn = QPushButton()
        self.batch_more_btn.setIcon(Theme.get_icon("more-horizontal", size=20, color=Theme.TEXT_MAIN))
        self.batch_more_btn.setToolTip(T("common.more"))
        self.batch_more_btn.setFixedSize(54, 40)
        self.batch_more_btn.setCursor(Qt.PointingHandCursor)
        self.batch_more_btn.setStyleSheet(Theme.get_discovery_action_btn_style('neutral'))
        
        self.batch_menu = QMenu(self)
        self.batch_menu.setStyleSheet(Theme.get_context_menu_style())
        
        fetch_lang_act = self.batch_menu.addAction(Theme.get_icon("globe", size=16, color=Theme.TEXT_MAIN), T("discovery.batch.fetch_language") if "discovery.batch.fetch_language" != T("discovery.batch.fetch_language") else "Fetch Missing Language")
        fetch_lang_act.triggered.connect(self._on_batch_fetch_languages)
        
        clear_act = self.batch_menu.addAction(Theme.get_icon("refresh", size=16, color=Theme.TEXT_MAIN), T("discovery.batch.clear"))
        clear_act.triggered.connect(self._on_batch_clear_requested)
        
        ignore_act = self.batch_menu.addAction(Theme.get_icon("trash-2", size=16, color=Theme.TEXT_MAIN), T("discovery.batch.ignore"))
        ignore_act.triggered.connect(self._on_batch_ignore_requested)
        
        self.batch_more_btn.setMenu(self.batch_menu)

        bb_layout.addWidget(self.batch_label)
        bb_layout.addStretch()
        bb_layout.addWidget(self.batch_restore_btn)
        bb_layout.addWidget(self.batch_more_btn)
        bb_layout.addSpacing(10)
        bb_layout.addWidget(self.batch_identify_btn)
        bb_layout.addSpacing(6)
        bb_layout.addWidget(self.batch_action_btn)
        self.batch_bar.hide()
        layout.addWidget(self.batch_bar)

    def _init_drop_overlay(self):
        self.drop_overlay = QFrame(self)
        self.drop_overlay.setObjectName("DropOverlay")
        self.drop_overlay.setStyleSheet(Theme.get_drop_overlay_style())
        self.drop_overlay.hide()
        overlay_layout = QVBoxLayout(self.drop_overlay)
        overlay_label = QLabel(T("discovery.messages.drop_ingest"))
        overlay_label.setStyleSheet(Theme.get_drop_overlay_label_style())
        overlay_label.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(overlay_label)
        self.setAcceptDrops(True)

    def _on_search_changed(self, text):
        self.review_view.tables['review'].apply_filters("all", text)
        self.review_view.tables['movies'].apply_filters("all", text)
        self.review_view.tables['shows'].apply_filters("all", text)
        self.conflicts_view.apply_filters("conflicts", text)
        for table in self.extras_view.tables.values():
            table.apply_filters("all", text)
        self.dropped_view.table.apply_filters("all", text)
        self.trash_view.apply_filters("ignored", text)

    def _get_active_table(self):
        idx = self.main_tabs.currentIndex()
        if idx == 0: return self.review_view.get_active_table()
        if idx == 1: return self.conflicts_view.table
        if idx == 2: return self.extras_view.get_active_table()
        if idx == 3: return self.dropped_view.table
        if idx == 4: return self.trash_view.table
        return None

    def refresh_data(self):
        if self.loader and self.loader.isRunning(): return
        self.progress_container.show()
        self.progress_bar.show()
        self.status_info.show()
        self.status_info.setText(T("discovery.messages.refreshing"))
        self.abort_btn.hide()
        self.progress_bar.setRange(0, 0) # Indeterminate for simple DB read
        self.loader = DataLoader(self.engine)
        self.loader.data_ready.connect(self._on_data_ready)
        self.loader.start()

    def _on_manual_scan_triggered(self):
        if self.sync_worker and self.sync_worker.isRunning(): return
        if self.loader and self.loader.isRunning(): return
        
        from PySide6.QtWidgets import QFileDialog
        
        start_dir = self.engine.config.settings.default_scan_path or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, T("discovery.messages.select_dir"), start_dir)
        
        if not path:
            return

        # Save as default if it's the first time
        if not self.engine.config.settings.default_scan_path:
            self.engine.config.settings.default_scan_path = path
            self.engine.config.save()

        self.progress_container.show()
        self.progress_bar.show()
        self.abort_btn.show()
        self.abort_btn.setEnabled(True)
        self.status_info.show()
        self._set_controls_enabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_info.setText(T("discovery.messages.starting_pipeline"))
        
        self.sync_worker = SyncWorker(self.engine, path)
        self.sync_worker.progress.connect(self._on_worker_progress)
        self.sync_worker.finished.connect(self._on_sync_finished)
        self.sync_worker.start()

    def _on_sync_finished(self):
        self.status_info.setText(T("discovery.messages.loading_list"))
        self.abort_btn.hide()
        self._set_controls_enabled(True)
        
        # Check for OMDB failure
        lib = getattr(self.engine.resolver, 'library', None)
        if lib:
            if getattr(lib, '_omdb_auth_failed', False):
                self.notif_bar.show_message(T("discovery.messages.omdb_auth_error"))
            if getattr(lib, '_omdb_limit_reached', False):
                QMessageBox.warning(self, T("common.warning"), T("discovery.messages.api_limit_reached"))
            
        self.refresh_data()

    def _on_data_ready(self, videos, poster_paths):
        # Reset progress bar to normal mode for next use
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_container.hide()
        self.progress_bar.hide()

        # 1. Detect Collisions (Skip Ignored files for collision detection)
        name_map = {} # target_name -> [vids]
        for v in videos:
            if v.get('match_status', '').upper() == 'IGNORED':
                continue
                
            target = v.get('_new_name')
            if target and target != "-":
                if target not in name_map: name_map[target] = []
                name_map[target].append(v)
        
        # 2. Split Data
        split_data = {"review": [], "movies": [], "shows": [], "extras": [], "dropped": [], "trash": [], "conflicts": []}
        
        # Track which IDs are already handled as conflicts to avoid duplication
        conflict_ids = set()
        for target, vids in name_map.items():
            if len(vids) > 1:
                for v in vids:
                    # Mark as conflict for the table renderer
                    v['_is_conflict'] = True 
                    split_data["conflicts"].append(v)
                    conflict_ids.add(v['id'])

        for v in videos:
            if v['id'] in conflict_ids:
                continue # Already in conflicts
                
            status = v.get('match_status', 'pending').upper()
            mtype = v.get('_media_type_from_db') or v.get('fn_media_type')
            cat = v.get('category', 'video')
            
            if status == 'IGNORED': split_data["trash"].append(v)
            elif v.get('is_manual'): split_data["dropped"].append(v)
            elif cat != 'video': split_data["extras"].append(v)
            elif status == 'MATCHED':
                if mtype == 'movie': split_data["movies"].append(v)
                else: split_data["shows"].append(v)
            else: split_data["review"].append(v)
        
        # Sort conflicts by target name to keep them grouped
        split_data["conflicts"].sort(key=lambda x: x.get('_new_name', ''))
        
        self.review_view.fill_data(split_data)
        self.conflicts_view.fill_data(split_data["conflicts"], is_conflicts=True)
        self.extras_view.fill_data(split_data["extras"])
        self.dropped_view.fill_data(split_data["dropped"])
        self.trash_view.fill_data(split_data["trash"])
        
        if poster_paths:
            self.poster_worker = PosterPrefetcher(self.engine, poster_paths)
            self.poster_worker.start()

    # --- Table Event Handlers ---
    def _setup_table_signals(self, table):
        table.itemSelectionChanged.connect(self._on_selection_changed)
        table.fix_requested.connect(self._on_fix_requested)
        table.manual_edit_requested.connect(self._on_manual_edit_requested)
        table.open_folder_requested.connect(self._on_open_folder_requested)
        table.ignore_requested.connect(self._on_ignore_requested)
        table.batch_ignore_requested.connect(self._on_batch_ignore_requested)
        table.batch_identify_requested.connect(self._on_batch_identify_requested)
        table.batch_edit_requested.connect(self._on_batch_actions_requested)
        table.fetch_language_requested.connect(self._start_language_fetch)
        table.clear_match_requested.connect(self._on_clear_match_requested)
        table.restore_requested.connect(self._on_restore_requested)

    def _load_poster(self, poster_path):
        if not poster_path: return None
        # Local cache path logic (mirrors LibraryManager)
        # discovery_page.py is in ui/v3/views/ (4 levels deep from root)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        local_path = os.path.join(base_dir, 'data', 'cache', 'posters', poster_path.lstrip('/'))
        if os.path.exists(local_path):
            return QPixmap(local_path)
        return None

    def _on_selection_changed(self):
        table = self._get_active_table()
        if not table: return
        selected = table.selectedItems()
        if not selected:
            self.inspector.set_empty()
            self.batch_bar.hide()
            return

        row = selected[0].row()
        self.inspector.set_empty() # Clear previous state
        file_id = table.item(row, 1).data(Qt.UserRole)
        file_data = self.engine.db.get_file_by_id(file_id)
        if file_data:
            self.inspector.update_tech_info(file_data)
            self.inspector.update_status(file_data.get('match_status', 'pending').upper())
            
            # Fetch links (Check parent for extras)
            target_id = file_data.get('parent_file_id') or file_id
            links = self.engine.db.media.get_links_for_file(target_id)
            
            if links:
                media = self.engine.db.media.get_media_item_by_id(links[0]['media_item_id'])
                if media:
                    self.inspector.update_from_data(media)
                    
                    if media.get('media_type') == 'tv':
                        # TV Show Layered Posters
                        series_pix = self._load_poster(media.get('poster_path'))
                        season_pix = None
                        all_episode_pix = []
                        
                        all_episodes_data = []
                        season_data = None
                        
                        # Collect all episodes from all links
                        for link in links:
                            if link.get('tv_episode_id'):
                                ep_data = self.engine.db.media.get_episode_by_id(link['tv_episode_id'])
                                if ep_data:
                                    all_episodes_data.append(ep_data)
                                    pix = self._load_poster(ep_data.get('still_path'))
                                    if pix: all_episode_pix.append(pix)
                                    
                                    if not season_data:
                                        season_data = self.engine.db.media.get_season_for_episode(link['tv_episode_id'])
                        
                        # Fallback: if no episode link or season not found, try to guess season from filename
                        if not season_data:
                            try:
                                s_num = file_data.get('fn_season') if file_data.get('fn_season') is not None else file_data.get('fd_season')
                                if s_num is not None:
                                    season_data = self.engine.db.media.get_season_by_number(media['id'], int(s_num))
                                    if season_data:
                                        season_pix = self._load_poster(season_data.get('poster_path'))
                            except: pass
                        elif not season_pix:
                            season_pix = self._load_poster(season_data.get('poster_path'))

                        self.inspector.poster_carousel.set_tv_posters(series_pix, season_pix, *all_episode_pix)
                        if all_episodes_data:
                            self.inspector.update_episode_info(all_episodes_data, season_data)
                        elif season_data:
                            # Show at least season info if no episode
                            self.inspector.update_episode_info([], season_data)
                    else:
                        # Movie Poster
                        pix = self._load_poster(media.get('poster_path'))
                        self.inspector.poster_carousel.set_single_poster(pix)
            else:
                # No Match: Check Candidates (Uncertain/Multiple)
                status = file_data.get('match_status', 'pending').upper()
                candidates = self.engine.db.matches.get_candidates(target_id)
                
                if candidates and status == 'UNCERTAIN':
                    # Show first candidate's poster for Uncertain
                    pix = self._load_poster(candidates[0].get('poster_path'))
                    self.inspector.poster_carousel.set_single_poster(pix)
                    self.inspector.title_label.setText(T("discovery.messages.candidate_prefix", title=candidates[0]['title']))
                else:
                    self.inspector.title_label.setText(file_data['file_name'])
                    self.inspector.poster_carousel.clear()

        unique_rows = set(item.row() for item in selected)
        if len(unique_rows) > 1:
            self.batch_label.setText(T("discovery.messages.items_selected", count=len(unique_rows)))
            
            # Special Trash View logic for Batch Bar
            is_trash = self.main_tabs.currentIndex() == 4
            if is_trash:
                self.batch_identify_btn.hide()
                self.batch_action_btn.hide()
                self.batch_more_btn.hide()
                self.batch_restore_btn.show()
            else:
                self.batch_identify_btn.show()
                self.batch_action_btn.show()
                self.batch_more_btn.show()
                self.batch_restore_btn.hide()
                
            self.batch_bar.show()
        else:
            self.batch_bar.hide()

    # --- Rename Flow ---
    def _on_apply_clicked(self):
        # 1. Check for Conflicts first
        conflicts = [f for f in self.engine.db.files.get_all_files() if f.get('match_status') == 'conflict']
        if conflicts:
            QMessageBox.warning(self, T("discovery.messages.global_conflicts_title"), 
                T("discovery.messages.global_conflicts_msg", count=len(conflicts)))
            self.main_tabs.setCurrentIndex(1) # Switch to Conflicts tab
            return

        self._set_controls_enabled(False)
        self.progress_container.show()
        self.progress_bar.show()
        self.abort_btn.show()
        self.status_info.show()
        self.status_info.setText(T("discovery.messages.generating_plan"))
        self.progress_bar.setRange(0, 0) # Indeterminate for plan generation
        self.plan_worker = PlanWorker(self.engine)
        self.plan_worker.plan_ready.connect(self._on_plan_ready)
        self.plan_worker.start()

    def _on_plan_ready(self, plan):
        self.progress_container.hide()
        
        if not plan:
            self._set_controls_enabled(True)
            QMessageBox.information(self, T("discovery.actions.apply"), T("discovery.messages.rename_empty"))
            return

        # 2. Check for Plan-level collisions (e.g. folder name overlaps)
        plan_conflicts = [item for item in plan if item.get('status') == 'collision']
        if plan_conflicts:
            self._set_controls_enabled(True)
            QMessageBox.warning(self, T("discovery.messages.conflicts_title"), 
                T("discovery.messages.conflicts_msg", count=len(plan_conflicts)))
            self.main_tabs.setCurrentIndex(1)
            return

        dialog = PreviewDialog(plan, self)
        if dialog.exec():
            self.progress_bar.show()
            self.status_info.show()
            self.worker = RenameWorker(self.engine, plan)
            self.worker.progress.connect(self._on_worker_progress)
            self.worker.finished.connect(self._on_rename_finished)
            self.worker.start()
        else:
            # Re-enable if user cancelled
            self._set_controls_enabled(True)

    def _on_worker_progress(self, val, text):
        if self.progress_bar.minimum() != 0 or self.progress_bar.maximum() != 100:
            self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(val)
        self.status_info.setText(text)
        # Force UI update if needed
        self.progress_bar.repaint()

    def _on_rename_finished(self, results):
        self.progress_container.hide()
        self.status_info.hide()
        self.abort_btn.hide()
        self._set_controls_enabled(True)
        
        success = results.get('success', 0)
        self.last_batch_id = results.get('batch_id')
        
        if success > 0:
            msg = T("discovery.messages.rename_success_notif", count=success)
            self.notif_bar.show_message(msg, batch_id=results.get('batch_id'), show_undo=True)
            
        if results.get('failed', 0) > 0:
            QMessageBox.warning(self, T("discovery.messages.rename_errors_title"), T("discovery.messages.rename_errors_msg", count=results['failed']))
            
        self.refresh_data()

    def _on_abort_clicked(self):
        self.abort_btn.setEnabled(False)
        self.status_info.setText(T("discovery.messages.aborting"))
        # Signal all possible workers
        for attr in ['sync_worker', 'worker', 'undo_worker']:
            w = getattr(self, attr, None)
            if w and w.isRunning():
                w.stop()

    def _set_controls_enabled(self, enabled):
        """Enables or disables main action buttons to prevent conflicting operations."""
        self.scan_new_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.apply_btn.setEnabled(enabled)
        self.main_tabs.setEnabled(enabled) # Also lock tabs for safety

    def _on_undo_requested(self, batch_id):
        if not batch_id: return
        
        if QMessageBox.question(self, T("common.undo"), T("discovery.messages.undo_confirm")) == QMessageBox.Yes:
            self._set_controls_enabled(False)
            self.progress_container.show()
            self.progress_bar.show()
            self.progress_bar.setRange(0, 100)
            self.status_info.show()
            self.status_info.setText(T("discovery.messages.undo_reverting"))
            
            self.undo_worker = UndoWorker(self.engine, batch_id)
            self.undo_worker.progress.connect(self._on_worker_progress)
            self.undo_worker.finished.connect(self._on_undo_finished)
            self.undo_worker.start()

    def _on_undo_finished(self, results):
        self.progress_container.hide()
        self.progress_bar.hide()
        self.status_info.hide()
        self._set_controls_enabled(True)
        self.last_batch_id = None
        
        success = results.get('success', 0)
        if success > 0:
            self.notif_bar.show_message(T("discovery.messages.undo_success", count=success), type='success')
        
        if results.get('failed', 0) > 0:
             QMessageBox.warning(self, T("discovery.messages.undo_errors_title"), T("discovery.messages.undo_errors_msg", count=results['failed']) + "\n\n" + "\n".join(results.get('errors', [])))
             
        self.refresh_data()

    def _on_batch_restore_requested(self):
        """Moves all selected items from Trash back to Review."""
        table = self._get_active_table()
        if not table: return
        
        file_ids = table.get_selected_ids()
        if not file_ids: return
        
        if QMessageBox.question(self, T("discovery.actions.restore"), T("discovery.messages.batch_restore_confirm", count=len(file_ids))) == QMessageBox.Yes:
            for fid in file_ids:
                self.engine.db.files.update_file(fid, {'match_status': 'pending'})
            self.refresh_data()

    def _on_fix_requested(self, vid):
        # Ensure we have full file data
        if 'file_name' not in vid:
            vid = self.engine.db.get_file_by_id(vid['id'])
            if not vid: return

        if vid.get('category') == 'video':
            if ManualResolveDialog(self.engine, vid).exec(): self.refresh_data()
        else:
            from ui.v3.components.edit_file_dialog import EditFileDialog
            if EditFileDialog(self, self.engine, vid).exec(): 
                self.refresh_data()

    def _on_manual_edit_requested(self, vid):
        # Ensure we have full file data
        if 'file_name' not in vid:
            vid = self.engine.db.get_file_by_id(vid['id'])
            if not vid: return

        from ui.v3.components.edit_file_dialog import EditFileDialog
        if EditFileDialog(self, self.engine, vid).exec(): 
            self.refresh_data()

    def _on_ignore_requested(self, file_id):
        self.engine.db.update_file(file_id, match_status='IGNORED')
        self.refresh_data()

    def _on_restore_requested(self, file_id, row_idx):
        self.engine.db.update_file(file_id, match_status='PENDING')
        self.refresh_data()

    def _on_clear_match_requested(self, file_id):
        self.engine.db.matches.clear_all_for_file(file_id)
        self.refresh_data()

    def _on_open_folder_requested(self, path):
        import subprocess
        if os.path.exists(os.path.dirname(path)):
            subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')

    def _on_batch_identify_requested(self):
        if self.sync_worker and self.sync_worker.isRunning(): return
        
        table = self._get_active_table()
        if not table: return
        ids = table.get_selected_ids()
        if not ids: return
        
        selected = [self.engine.db.files.get_file_by_id(fid) for fid in ids]
        selected = [f for f in selected if f]
        
        if BatchResolveDialog(self.engine, selected, self).exec():
            self.refresh_data()

    def _on_batch_actions_requested(self):
        table = self._get_active_table()
        if not table: return
        ids = table.get_selected_ids()
        if not ids: return

        selected = [self.engine.db.files.get_file_by_id(fid) for fid in ids]
        selected = [f for f in selected if f]
        
        if BatchOperationsDialog(self.engine, selected, self).exec():
            self.refresh_data()

    def _on_batch_ignore_requested(self):
        table = self._get_active_table()
        if not table: return
        ids = table.get_selected_ids()
        if not ids: return
        
        is_trash = self.main_tabs.currentIndex() == 4
        action_title = T("discovery.actions.restore") if is_trash else T("discovery.actions.ignore")
        confirm_msg = T("discovery.messages.restore_confirm", count=len(ids)) if is_trash else T("discovery.messages.ignore_confirm", count=len(ids))
        
        if QMessageBox.question(self, action_title, confirm_msg) == QMessageBox.Yes:
            for fid in ids:
                new_status = 'PENDING' if is_trash else 'IGNORED'
                self.engine.db.files.update_file(fid, match_status=new_status)
            self.refresh_data()

    def _on_batch_clear_requested(self):
        table = self._get_active_table()
        if not table: return
        ids = table.get_selected_ids()
        if not ids: return
        
        if QMessageBox.question(self, T("discovery.actions.batch_actions"), 
            T("discovery.messages.clear_confirm", count=len(ids))) == QMessageBox.Yes:
            for fid in ids:
                self.engine.db.matches.clear_all_for_file(fid)
            self.refresh_data()

    def _on_batch_fetch_languages(self):
        table = self._get_active_table()
        if not table: return
        ids = table.get_selected_ids()
        if not ids: return
        self._start_language_fetch(ids)

    def notify_language_changed(self, new_lang):
        """Triggered from MainWindow when settings change the language."""
        self.inspector.set_preferred_language(new_lang)
        msg = T("discovery.messages.language_changed", lang=new_lang) if "discovery.messages.language_changed" != T("discovery.messages.language_changed") else f"Language changed to {new_lang}. Fetch new metadata?"
        self.notif_bar.show_custom_action(msg, T("discovery.actions.fetch") if "discovery.actions.fetch" != T("discovery.actions.fetch") else "Fetch", payload="smart_fetch")

    def _on_custom_action_requested(self, payload):
        if payload == "smart_fetch":
            self._start_language_fetch(None)

    def _start_language_fetch(self, item_ids=None):
        from ui.v3.workers.discovery_workers import LanguageFetchWorker
        self._set_controls_enabled(False)
        self.progress_container.show()
        self.progress_bar.show()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_info.show()
        self.status_info.setText("Fetching missing metadata languages...")
        
        self.worker = LanguageFetchWorker(self.engine, item_ids)
        self.active_workers.append(self.worker)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.finished.connect(self._on_fetch_languages_finished)
        self.worker.start()

    def _on_worker_progress(self, val, text):
        self.progress_bar.setValue(val)
        self.status_info.setText(text)

    def _on_fetch_languages_finished(self):
        self.progress_bar.hide()
        self.status_info.hide()
        self._set_controls_enabled(True)
        self.refresh_data()
        self.notif_bar.show_message("Language fetching complete.", duration=3000)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.drop_overlay.show()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event): self.drop_overlay.hide()

    def dropEvent(self, event):
        self.drop_overlay.hide()
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.main_tabs.setCurrentIndex(2) # Dropped tab
            self.drop_worker = DropProcessor(self.engine, paths)
            self.drop_worker.finished.connect(self.refresh_data)
            self.drop_worker.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.drop_overlay.setGeometry(self.rect())

    def refresh_style(self):
        """Forces a re-application of all dynamic styles."""
        self.search_box.setStyleSheet(Theme.get_input_style())
        
        self.scan_new_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.scan_new_btn.setIcon(Theme.get_icon("search", size=16, color=Theme.TEXT_MAIN))
        
        self.refresh_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.refresh_btn.setIcon(Theme.get_icon("refresh", size=16, color=Theme.TEXT_MAIN))
        
        self.main_tabs.setStyleSheet(Theme.get_tab_widget_style())
        self.apply_btn.setStyleSheet(Theme.get_primary_button_style())
        
        # Progress Bar
        self.progress_bar.setStyleSheet(Theme.get_progress_bar_detailed_style())
        self.status_info.setStyleSheet(Theme.get_status_label_style())
        self.abort_btn.setStyleSheet(Theme.get_abort_button_style())
        
        # Batch Bar
        self.batch_bar.setStyleSheet(Theme.get_batch_bar_style())
        self.batch_label.setStyleSheet(Theme.get_batch_label_style())
        
        # Inspector
        self.inspector.setStyleSheet(Theme.get_inspector_style())
        if hasattr(self.inspector, 'refresh_style'):
            self.inspector.refresh_style()
        
        # Overlay
        self.drop_overlay.setStyleSheet(Theme.get_drop_overlay_style())
