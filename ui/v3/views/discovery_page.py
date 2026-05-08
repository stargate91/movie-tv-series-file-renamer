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
from ui.v3.logic.discovery_controller import DiscoveryController
from core.i18n import T

# Modular Views
from ui.v3.components.discovery.review_view import ReviewView
from ui.v3.components.discovery.dropped_view import DroppedView
from ui.v3.components.discovery.extras_view import ExtrasView
from ui.v3.components.discovery.conflicts_view import ConflictsView
from ui.v3.components.discovery.trash_view import TrashView
from ui.v3.components.discovery.batch_bar import BatchBar

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
        
        # Initialize Controller
        self.controller = DiscoveryController(self.engine)
        self._init_controller_connections()
        
        self._init_ui()
        QTimer.singleShot(100, self.controller.refresh_data)

    def _init_controller_connections(self):
        """Wire controller signals to page UI updates."""
        self.controller.refresh_requested.connect(self.controller.refresh_data) # Controller can trigger its own refresh
        self.controller.operation_started.connect(self._on_operation_started)
        self.controller.operation_finished.connect(self._on_operation_finished)
        self.controller.progress_updated.connect(self._on_worker_progress)
        self.controller.error_occurred.connect(lambda t, m: QMessageBox.critical(self, t, m))
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 1. Header
        self._setup_header(layout)

        # 2. Tabs & Inspector
        self._setup_main_content(layout)

        # 3. Status Area
        self._setup_status_area(layout)

        # 4. Batch Bar
        self.batch_bar = BatchBar()
        self.batch_bar.actions_requested.connect(self._on_batch_actions_requested)
        self.batch_bar.identify_requested.connect(self._on_batch_identify_requested)
        self.batch_bar.fetch_requested.connect(self._on_batch_fetch_languages)
        self.batch_bar.restore_requested.connect(self._on_batch_restore_requested)
        self.batch_bar.clear_requested.connect(self._on_batch_clear_requested)
        self.batch_bar.ignore_requested.connect(self._on_batch_ignore_requested)
        self.batch_bar.organize_requested.connect(self._on_batch_organize_requested)
        self.batch_bar.open_folder_requested.connect(self._on_batch_open_folder)
        layout.addWidget(self.batch_bar)

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

    def _setup_header(self, layout):
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

        self.refresh_btn = QPushButton(T("discovery.actions.refresh"))
        self.refresh_btn.setIcon(Theme.get_icon("refresh", size=16, color=Theme.TEXT_MAIN))
        self.refresh_btn.setFixedWidth(140)
        self.refresh_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.refresh_btn.clicked.connect(self.controller.refresh_data)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.search_box)
        header.addWidget(self.scan_new_btn)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

    def _setup_main_content(self, layout):
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet(Theme.get_tab_widget_style())

        self.review_view = ReviewView(self.engine)
        self.conflicts_view = ConflictsView(self.engine)
        self.extras_view = ExtrasView(self.engine)
        self.dropped_view = DroppedView(self.engine)
        self.trash_view = TrashView(self.engine)

        self.main_tabs.addTab(self.review_view, Theme.get_icon("search", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.library"))
        self.main_tabs.addTab(self.conflicts_view, Theme.get_icon("alert-triangle", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.conflicts"))
        self.main_tabs.addTab(self.extras_view, Theme.get_icon("paperclip", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.extras"))
        self.main_tabs.addTab(self.dropped_view, Theme.get_icon("package", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.dropped"))
        self.main_tabs.addTab(self.trash_view, Theme.get_icon("trash-2", size=16, color=Theme.TEXT_MUTED), T("discovery.tabs.trash"))
        self.dropped_view.refresh_requested.connect(self.controller.refresh_data)
        for view in [self.review_view, self.conflicts_view, self.extras_view, self.dropped_view, self.trash_view]:
            if isinstance(view, DiscoveryTable): self._setup_table_signals(view)
            else:
                # Wire all tables in views that have sub-tabs or a single table
                if hasattr(view, 'tables'):
                    for table in view.tables.values(): self._setup_table_signals(table)
                if hasattr(view, 'table'): self._setup_table_signals(view.table)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        content_layout.addWidget(self.main_tabs, 7)
        
        self.inspector = InspectorPanel()
        self.inspector.set_preferred_language(self.engine.config.settings.metadata_language)
        self.inspector.enrichment_finished.connect(self.controller.refresh_data)
        
        content_layout.addWidget(self.inspector, 3)
        layout.addLayout(content_layout)

    def _setup_status_area(self, layout):
        self.progress_container = QWidget()
        self.progress_container.hide()
        p_layout = QVBoxLayout(self.progress_container)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.setSpacing(8)
        
        # Abort Row
        status_row = QHBoxLayout()
        self.status_info = QLabel("")
        self.status_info.setStyleSheet(Theme.get_status_label_style())
        
        self.abort_btn = QPushButton(T("discovery.buttons.abort"))
        self.abort_btn.setObjectName("abort-btn")
        self.abort_btn.setFixedSize(130, 28)
        self.abort_btn.setStyleSheet(Theme.get_abort_button_style())
        self.abort_btn.clicked.connect(self._on_abort_clicked)
        self.abort_btn.hide()
        
        status_row.addWidget(self.status_info)
        status_row.addStretch()
        status_row.addWidget(self.abort_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setStyleSheet(Theme.get_progress_bar_detailed_style())
        
        p_layout.addLayout(status_row)
        p_layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_container)



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
        self.dropped_view.apply_filters("all", text)
        self.trash_view.apply_filters("ignored", text)

    def _get_active_table(self):
        idx = self.main_tabs.currentIndex()
        if idx == 0: return self.review_view.get_active_table()
        if idx == 1: return self.conflicts_view.get_active_table()
        if idx == 2: return self.extras_view.get_active_table()
        if idx == 3: return self.dropped_view.get_active_table()
        if idx == 4: return self.trash_view.table
        return None

    # REMOVED: redundant refresh_data (delegated to controller)

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

        # Use centralized controller for the scan
        self.controller.start_scan(path)



    # --- Table Event Handlers ---
    def refresh_data(self):
        """Proxy for the controller's refresh logic."""
        self.controller.refresh_data()

    def _setup_table_signals(self, table):
        table.itemSelectionChanged.connect(self._on_selection_changed)
        table.action_triggered.connect(self._on_action_triggered)
        
    def _on_action_triggered(self, action_id: str, item_ids: list):
        """Routes actions from tables to the controller."""
        if not item_ids: return

        if action_id == 'restore':
            confirm_msg = T("discovery.messages.batch_restore_confirm", count=len(item_ids))
            if QMessageBox.question(self, T("discovery.actions.restore"), confirm_msg) == QMessageBox.Yes:
                self.controller.batch_restore(item_ids)
        elif action_id == 'ignore':
            is_dropped = self.main_tabs.currentIndex() == 3
            action_title = T("discovery.actions.delete") if is_dropped else T("discovery.actions.ignore")
            confirm_msg = T("discovery.messages.batch_delete_confirm", count=len(item_ids)) if is_dropped else T("discovery.messages.batch_ignore_confirm", count=len(item_ids))
            
            if QMessageBox.question(self, action_title, confirm_msg) == QMessageBox.Yes:
                if is_dropped: self.controller.batch_delete(item_ids)
                else: self.controller.batch_ignore(item_ids)
        elif action_id == 'clear_match':
            confirm_msg = T("discovery.messages.clear_confirm", count=len(item_ids))
            if QMessageBox.question(self, T("discovery.actions.batch_actions"), confirm_msg) == QMessageBox.Yes:
                self.controller.batch_clear_matches(item_ids)
        elif action_id == 'fetch_language':
            self.controller.start_language_fetch(item_ids)
        elif action_id == 'organize':
            confirm_msg = T("discovery.messages.batch_organize_confirm", count=len(item_ids))
            if len(item_ids) == 1 or QMessageBox.question(self, T("discovery.actions.organize"), confirm_msg) == QMessageBox.Yes:
                self.controller.batch_organize(item_ids)
        elif action_id == 'fix':
            if len(item_ids) == 1:
                self._on_fix_requested({'id': item_ids[0]})
            else:
                self._on_batch_identify_requested()
        elif action_id == 'edit':
            if len(item_ids) == 1:
                self._on_manual_edit_requested({'id': item_ids[0]})
            else:
                self._on_batch_actions_requested()
        elif action_id == 'open_folder':
            vid = self.engine.db.files.get_file_by_id(item_ids[0])
            if vid: self._on_open_folder_requested(vid['current_path'])



    def _on_selection_changed(self):
        table = self._get_active_table()
        if not table: return
        selected = table.selectedItems()
        if not selected:
            self.inspector.set_empty()
            self.batch_bar.hide()
            return

        # 1. Update Inspector
        row = selected[0].row()
        file_id = table.item(row, 1).data(Qt.UserRole)
        self.inspector.set_file(file_id, self.engine)

        # 2. Update Batch Bar
        unique_rows = set(item.row() for item in selected)
        tab_idx = self.main_tabs.currentIndex()
        is_trash = tab_idx == 4
        
        # Determine category based on active view
        category = 'video'
        if tab_idx == 2:  # Extras tab
            category = 'extra'
        elif tab_idx == 1:  # Conflicts - check active sub-tab
            if self.conflicts_view._has_subtabs:
                if self.conflicts_view.tabs.currentIndex() == 1:
                    category = 'extra'
            else:
                # If no subtabs, determine category from the selection
                first_row = unique_rows.copy().pop()
                cat_item = table.item(first_row, 2)
                if cat_item and cat_item.data(Qt.UserRole) != 'video':
                    category = 'extra'
        elif tab_idx == 3:  # Dropped - check active sub-tab
            if self.dropped_view._has_subtabs:
                if self.dropped_view.tabs.currentIndex() == 1:
                    category = 'extra'
            else:
                first_row = unique_rows.copy().pop()
        # Check if all selected items are matched
        all_matched = True
        for r in unique_rows:
            st_item = table.item(r, 0)
            if st_item and st_item.data(Qt.UserRole) != 'MATCHED':
                all_matched = False
                break
            
        self.batch_bar.set_selection_count(len(unique_rows), is_trash, category, all_matched=all_matched)

    # --- Rename Flow ---
    def _on_apply_clicked(self):
        # 1. Check for Conflicts first
        conflicts = [f for f in self.engine.db.files.get_all_files() if f.get('match_status') == 'conflict']
        if conflicts:
            QMessageBox.warning(self, T("discovery.messages.global_conflicts_title"), 
                T("discovery.messages.global_conflicts_msg", count=len(conflicts)))
            self.main_tabs.setCurrentIndex(1)
            return

        videos = [f for f in self.engine.db.files.get_all_files() if f.get('match_status') != 'IGNORED']
        self.controller.start_rename_plan(videos)

    def _on_abort_clicked(self):
        self.abort_btn.setEnabled(False)
        self.controller.abort_all()
        # Also stop page-specific workers
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
            self.controller.start_undo(batch_id)

    def _on_batch_restore_requested(self):
        """Moves all selected items from Trash back to Review."""
        table = self._get_active_table()
        if not table: return
        file_ids = table.get_selected_ids()
        if not file_ids: return
        
        if QMessageBox.question(self, T("discovery.actions.restore"), T("discovery.messages.batch_restore_confirm", count=len(file_ids))) == QMessageBox.Yes:
            self.controller.batch_restore(file_ids)

    def _on_fix_requested(self, vid):
        # Ensure we have full file data
        if 'file_name' not in vid:
            vid = self.engine.db.get_file_by_id(vid['id'])
            if not vid: return

        if vid.get('category') == 'video':
            if ManualResolveDialog(self.engine, vid).exec(): self.controller.refresh_data()
        else:
            from ui.v3.components.edit_file_dialog import EditFileDialog
            if EditFileDialog(self, self.engine, vid).exec(): 
                self.controller.refresh_data()

    def _on_manual_edit_requested(self, vid):
        # Ensure we have full file data
        if 'file_name' not in vid:
            vid = self.engine.db.get_file_by_id(vid['id'])
            if not vid: return

        from ui.v3.components.edit_file_dialog import EditFileDialog
        if EditFileDialog(self, self.engine, vid).exec(): 
            self.controller.refresh_data()



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
            self.controller.refresh_data()

    def _on_batch_actions_requested(self):
        table = self._get_active_table()
        if not table: return
        ids = table.get_selected_ids()
        if not ids: return

        selected = [self.engine.db.files.get_file_by_id(fid) for fid in ids]
        selected = [f for f in selected if f]
        
        if BatchOperationsDialog(self.engine, selected, self).exec():
            self.controller.refresh_data()

    def _on_batch_open_folder(self):
        table = self._get_active_table()
        if not table: return
        paths = table.get_selected_paths()
        if paths:
            self._on_open_folder_requested(paths[0])

    def _on_batch_ignore_requested(self):
        table = self._get_active_table()
        if not table: return
        ids = table.get_selected_ids()
        if not ids: return
        
        is_trash = self.main_tabs.currentIndex() == 4
        is_dropped = self.main_tabs.currentIndex() == 3
        
        if is_trash:
            action_title = T("discovery.actions.restore")
            confirm_msg = T("discovery.messages.batch_restore_confirm", count=len(ids))
        elif is_dropped:
            action_title = T("discovery.actions.delete")
            confirm_msg = T("discovery.messages.batch_delete_confirm", count=len(ids))
        else:
            action_title = T("discovery.actions.ignore")
            confirm_msg = T("discovery.messages.batch_ignore_confirm", count=len(ids))
        
        if QMessageBox.question(self, action_title, confirm_msg) == QMessageBox.Yes:
            if is_trash: self.controller.batch_restore(ids)
            elif is_dropped: self.controller.batch_delete(ids)
            else: self.controller.batch_ignore(ids)

    def _on_batch_clear_requested(self):
        table = self._get_active_table()
        if not table: return
        ids = table.get_selected_ids()
        if not ids: return
        
        if QMessageBox.question(self, T("discovery.actions.batch_actions"), 
            T("discovery.messages.clear_confirm", count=len(ids))) == QMessageBox.Yes:
            self.controller.batch_clear_matches(ids)

    def _on_batch_fetch_languages(self):
        table = self._get_active_table()
        if not table: return
        ids = table.get_selected_ids()
        if not ids: return
        self.controller.start_language_fetch(ids)

    def _on_batch_organize_requested(self):
        table = self._get_active_table()
        if not table: return
        ids = table.get_selected_ids()
        if not ids: return
        
        confirm_msg = T("discovery.messages.batch_organize_confirm", count=len(ids))
        if QMessageBox.question(self, T("discovery.actions.organize"), confirm_msg) == QMessageBox.Yes:
            self.controller.batch_organize(ids)

    def _on_operation_started(self, message: str):
        self.progress_container.show()
        self.progress_bar.show()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_info.show()
        self.status_info.setText(message)
        self.abort_btn.show()
        self.abort_btn.setEnabled(True)
        self._set_controls_enabled(False)

    def _on_operation_finished(self, results: dict):
        self.progress_container.hide()
        self.status_info.hide()
        self.abort_btn.hide()
        self._set_controls_enabled(True)
        
        op_type = results.get('type')
        if op_type == 'data_ready':
            split_data = self.controller.split_data(results['videos'])
            self.review_view.fill_data(split_data)
            self.conflicts_view.fill_data(split_data["conflicts"], is_conflicts=True)
            self.extras_view.fill_data(split_data["extras"])
            self.dropped_view.fill_data(split_data["dropped"])
            self.trash_view.fill_data(split_data["trash"])

        elif op_type == 'plan_ready':
            plan = results['plan']
            if not plan:
                QMessageBox.information(self, T("discovery.actions.apply"), T("discovery.messages.rename_empty"))
                return
            
            # Check collisions
            coll = [i for i in plan if i.get('status') == 'collision']
            if coll:
                QMessageBox.warning(self, T("discovery.messages.conflicts_title"), T("discovery.messages.conflicts_msg", count=len(coll)))
                self.main_tabs.setCurrentIndex(1)
                return
                
            if PreviewDialog(plan, self).exec():
                self.controller.execute_rename(plan)

        elif op_type == 'rename_complete':
            res = results['results']
            success = res.get('success', 0)
            if success > 0:
                self.notif_bar.show_message(T("discovery.messages.rename_success_notif", count=success), 
                                          batch_id=res.get('batch_id'), show_undo=True)
            if res.get('failed', 0) > 0:
                QMessageBox.warning(self, T("discovery.messages.rename_errors_title"), T("discovery.messages.rename_errors_msg", count=res['failed']))

        elif op_type == 'undo_complete':
            res = results['results']
            success = res.get('success', 0)
            if success > 0:
                self.notif_bar.show_message(T("discovery.messages.undo_success", count=success), type='success')
            if res.get('failed', 0) > 0:
                QMessageBox.warning(self, T("discovery.messages.undo_errors_title"), T("discovery.messages.undo_errors_msg", count=res['failed']))

        elif op_type == 'fetch':
            self.notif_bar.show_message("Language fetching complete.", duration=3000)
        elif op_type == 'scan':
            self.notif_bar.show_message("Scan complete.", duration=3000)

    def _on_worker_progress(self, val, text):
        self.progress_bar.setValue(val)
        self.status_info.setText(text)

    def notify_language_changed(self, new_lang):
        """Triggered from MainWindow when settings change the language."""
        self.inspector.set_preferred_language(new_lang)
        msg = T("discovery.messages.language_changed", lang=new_lang)
        self.notif_bar.show_custom_action(msg, T("discovery.actions.fetch"), payload="smart_fetch")

    def _on_custom_action_requested(self, payload):
        if payload == "smart_fetch":
            self.controller.start_language_fetch(None)

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
            self.drop_worker.finished.connect(self.controller.refresh_data)
            self.drop_worker.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.drop_overlay.setGeometry(self.rect())

    def refresh_style(self):
        """Forces a re-application of all dynamic styles."""
        self.search_box.setStyleSheet(Theme.get_input_style())
        self.scan_new_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.refresh_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.main_tabs.setStyleSheet(Theme.get_tab_widget_style())
        self.apply_btn.setStyleSheet(Theme.get_primary_button_style())
        
        # Progress Bar
        self.progress_bar.setStyleSheet(Theme.get_progress_bar_detailed_style())
        self.status_info.setStyleSheet(Theme.get_status_label_style())
        self.abort_btn.setStyleSheet(Theme.get_abort_button_style())
        
        # Modular
        self.batch_bar.refresh_style()
        self.inspector.refresh_style()
        self.drop_overlay.setStyleSheet(Theme.get_drop_overlay_style())
