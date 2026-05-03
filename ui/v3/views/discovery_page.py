import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QLineEdit, QApplication,
                             QTableWidgetItem, QHeaderView, QLabel, QFrame, QPushButton, QProgressBar, QMessageBox, QDialog, QStyledItemDelegate, QStyle)
from PySide6.QtGui import QColor, QPixmap, QLinearGradient, QPainter, QPalette
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRect
from ui.v3.styles.theme import Theme
from ui.v3.components.inspector_panel import InspectorPanel
from ui.v3.components.manual_resolve_dialog import ManualResolveDialog
from ui.v3.components.preview_dialog import PreviewDialog

class PremiumDelegate(QStyledItemDelegate):
    """Custom delegate to draw premium row selection with a left accent bar."""
    def paint(self, painter, option, index):
        # Default drawing for non-selected items (or if it's a cell widget column)
        # Note: cellWidgets are handled separately by Qt, but we still paint the background
        
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw Row Background
        if option.state & QStyle.State_Selected:
            # Draw the indigo gradient background
            grad = QLinearGradient(option.rect.topLeft(), option.rect.topRight())
            grad.setColorAt(0, QColor(Theme.PRIMARY))
            grad.setColorAt(0.005, QColor(Theme.PRIMARY))
            grad.setColorAt(0.007, QColor(Theme.SURFACE_LIGHT))
            grad.setColorAt(1.0, QColor(Theme.SURFACE_DARK))
            
            painter.fillRect(option.rect, grad)
            
            # Draw left accent bar (3px)
            accent_rect = QRect(option.rect.left(), option.rect.top(), 4, option.rect.height())
            painter.fillRect(accent_rect, QColor(Theme.PRIMARY))
        else:
            # Normal background
            if option.state & QStyle.State_MouseOver:
                painter.fillRect(option.rect, QColor(Theme.SURFACE_LIGHT + "40"))
            else:
                # We let the table's background show through
                pass

        painter.restore()

        # Draw the actual text/content
        # If there's a cell widget (Col 0 and 4), we don't draw text here
        if index.column() not in (0, 4):
            super().paint(painter, option, index)

class DataLoader(QThread):
    """Background thread for loading data and collecting poster paths."""
    data_ready = Signal(list, list)  # videos, poster_paths

    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def run(self):
        try:
            raw_videos = self.engine.db.get_files_by_category('video', 'extra', 'subtitle', 'audio', 'image', 'metadata', 'unknown')
            # Filter out files that are already completed (renamed) or deleted
            videos = [v for v in raw_videos if v.get('status') not in ('renamed', 'deleted')]
            
            status_priority = {'multiple': 0, 'no_match': 1, 'uncertain': 2, 'matched': 3, 'pending': 4}
            videos.sort(key=lambda v: status_priority.get(v.get('match_status', 'pending'), 99))

            # Collect poster paths and generate preview names here (off main thread)
            poster_paths = []
            for vid in videos:
                try:
                    # Pre-generate the new name for the preview column
                    new_name = self.engine.formatter.generate_name(vid['id'], self.engine.config.settings)
                    if new_name:
                        import os
                        ext = os.path.splitext(vid.get('file_name', ''))[1]
                        vid['_new_name'] = f"{new_name}{ext}"
                        
                    # Fetch links (use parent_id if extra)
                    target_id = vid.get('parent_file_id') or vid['id']
                    links = self.engine.db.get_links_for_file(target_id)
                    if links:
                        media = self.engine.db.get_media_item_by_id(links[0]['media_item_id'])
                        if media and media.get('poster_path'):
                            poster_paths.append(media['poster_path'])
                except:
                    pass

            self.data_ready.emit(videos, poster_paths)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"DataLoader Error: {e}")
            self.data_ready.emit([], [])

class PosterPrefetcher(QThread):
    """Prefetches poster images in the background."""
    def __init__(self, engine, poster_paths):
        super().__init__()
        self.engine = engine
        self.poster_paths = poster_paths

    def run(self):
        for path in self.poster_paths:
            if not path: continue
            try:
                self.engine.db.api_cache.get_poster(path)
            except:
                pass

class RenameWorker(QThread):
    """Handles the physical renaming process in the background."""
    finished = Signal(dict)

    def __init__(self, engine, plan):
        super().__init__()
        self.engine = engine
        self.plan = plan

    def run(self):
        try:
            results = self.engine.apply_plan(self.plan)
            self.finished.emit(results)
        except Exception as e:
            self.finished.emit({'success': 0, 'failed': 1, 'skipped': 0, 'deleted': 0, 'errors': [str(e)]})

class PlanWorker(QThread):
    """Handles the heavy lifting of generating the rename plan."""
    plan_ready = Signal(list)
    error = Signal(str)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def run(self):
        try:
            plan = self.engine.get_rename_plan()
            self.plan_ready.emit(plan)
        except Exception as e:
            self.error.emit(str(e))

class DiscoveryPage(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.loader = None
        self.poster_worker = None
        self.active_workers = [] # Keep references to prevent GC crashes
        self.current_filter = "all" # 'all', 'review', 'movies', 'shows'
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header Area
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Discovery")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        
        self.stats_label = QLabel("0 files found")
        self.stats_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-weight: 600;")
        # Action Buttons Area
        actions_layout = QHBoxLayout()
        self.scan_new_btn = QPushButton("Scan New Directory")
        self.scan_new_btn.setObjectName("SecondaryButton")
        self.scan_new_btn.setFixedWidth(180)
        self.scan_new_btn.setCursor(Qt.PointingHandCursor)

        self.rename_all_btn = QPushButton("Apply Renames")
        self.rename_all_btn.setFixedWidth(180)
        self.rename_all_btn.setCursor(Qt.PointingHandCursor)
        self.rename_all_btn.setStyleSheet(Theme.get_primary_button_style())
        self.rename_all_btn.hide() # Only show if we have matched items
        
        actions_layout.addWidget(self.stats_label)
        actions_layout.addSpacing(20)
        actions_layout.addWidget(self.scan_new_btn)
        actions_layout.addWidget(self.rename_all_btn)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addLayout(actions_layout)
        layout.addLayout(header_layout)

        # Filters Area
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)
        
        # Filter Buttons
        self.filter_btns = []
        
        btn_all = QPushButton("All Files")
        btn_all.setCheckable(True)
        btn_all.setChecked(True)
        btn_all.setProperty("filter_val", "all")
        
        btn_review = QPushButton("Needs Review")
        btn_review.setCheckable(True)
        btn_review.setProperty("filter_val", "review")
        
        btn_movies = QPushButton("Matched Movies")
        btn_movies.setCheckable(True)
        btn_movies.setProperty("filter_val", "movies")
        
        btn_shows = QPushButton("Matched Shows")
        btn_shows.setCheckable(True)
        btn_shows.setProperty("filter_val", "shows")
        
        btn_extras = QPushButton("Extras")
        btn_extras.setCheckable(True)
        btn_extras.setProperty("filter_val", "extras")
        
        btn_ignored = QPushButton("Trash")
        btn_ignored.setCheckable(True)
        btn_ignored.setProperty("filter_val", "ignored")
        btn_ignored.setStyleSheet("color: #EF4444;")
        
        self.filter_btns.extend([btn_all, btn_review, btn_movies, btn_shows, btn_extras, btn_ignored])
        
        for btn in self.filter_btns:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setStyleSheet(Theme.get_filter_chip_style())
            btn.clicked.connect(lambda checked, b=btn: self._on_filter_btn_clicked(b))
            filters_layout.addWidget(btn)
        
        filters_layout.addStretch()
        
        # Search Box
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search titles...")
        self.filter_input.setFixedWidth(250)
        self.filter_input.setFixedHeight(32)
        self.filter_input.textChanged.connect(self._apply_filters)
        filters_layout.addWidget(self.filter_input)
        
        layout.addLayout(filters_layout)
        layout.addSpacing(10)

        # Progress Section
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(Theme.get_progress_bar_style())
        self.progress_bar.hide()
        
        self.status_info = QLabel("")
        self.status_info.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: 600; font-size: 11px;")
        self.status_info.hide()

        layout.addWidget(self.status_info)
        layout.addWidget(self.progress_bar)
        
        # Batch Action Bar
        self.batch_bar = QFrame()
        self.batch_bar.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(99, 102, 241, 0.1); /* Primary color with transparency */
                border: 1px solid {Theme.PRIMARY};
                border-radius: 8px;
            }}
        """)
        self.batch_bar.setFixedHeight(50)
        self.batch_bar.hide()
        
        batch_layout = QHBoxLayout(self.batch_bar)
        
        self.batch_count_lbl = QLabel("0 files selected")
        self.batch_count_lbl.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        
        btn_deselect = QPushButton("✖ Deselect All")
        btn_deselect.setCursor(Qt.PointingHandCursor)
        btn_deselect.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {Theme.TEXT_MAIN}; border: none; font-weight: bold; }}
            QPushButton:hover {{ color: white; }}
        """)
        btn_deselect.clicked.connect(self._deselect_all)
        
        self.batch_ignore_btn = QPushButton("🗑 Ignore Selected")
        self.batch_ignore_btn.setCursor(Qt.PointingHandCursor)
        self.batch_ignore_btn.setStyleSheet(f"""
            QPushButton {{ background: {Theme.ERROR}; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background: #DC2626; }}
        """)
        self.batch_ignore_btn.clicked.connect(self._ignore_selected)
        
        batch_layout.addWidget(self.batch_count_lbl)
        batch_layout.addStretch()
        batch_layout.addWidget(btn_deselect)
        batch_layout.addWidget(self.batch_ignore_btn)
        
        layout.addWidget(self.batch_bar)
        layout.addSpacing(10)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0) # No gap between them for a seamless look

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Status", "Original Name", "Type", "New Name Preview", "Actions"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers) # Disable inline editing
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Style the table
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection) # Enable Shift+Click / Ctrl+Click
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        
        # Aggressive palette override for Windows native selection
        from PySide6.QtGui import QPalette, QColor
        pal = self.table.palette()
        pal.setColor(QPalette.Highlight, QColor(0, 0, 0, 0)) # Fully transparent highlight
        pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.table.setPalette(pal)

        # Install custom delegate for premium selection painting
        self.table.setItemDelegate(PremiumDelegate(self.table))

        # Use centralized premium styling (Delegate handles the selection background)
        self.table.setStyleSheet(Theme.get_discovery_table_style())
        
        # Header styling
        header = self.table.horizontalHeader()
        
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 100) # Status
        
        header.setSectionResizeMode(1, QHeaderView.Stretch) # Original Name
        
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 100) # Type
        
        header.setSectionResizeMode(3, QHeaderView.Stretch) # Identified As
        
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 180) # Actions
        
        header.setDefaultAlignment(Qt.AlignLeft)
        
        # Ensure row height is enough for buttons
        self.table.verticalHeader().setDefaultSectionSize(45)
        
        content_layout.addWidget(self.table)


        # 2. Inspector Panel
        self.inspector = InspectorPanel()
        content_layout.addWidget(self.inspector)

        layout.addLayout(content_layout)

        # Signals
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.rename_all_btn.clicked.connect(self._on_rename_all_clicked)
        
        # Explicit Ctrl+A support
        from PySide6.QtGui import QShortcut, QKeySequence
        self.shortcut_select_all = QShortcut(QKeySequence("Ctrl+A"), self)
        self.shortcut_select_all.activated.connect(self.table.selectAll)
        
        # Delete key support
        self.shortcut_delete = QShortcut(QKeySequence.Delete, self)
        self.shortcut_delete.activated.connect(self._ignore_selected)

    def _update_rows_natively(self, parent_file_id):
        """Instantly updates the UI for a file and its children without rebuilding the whole table."""
        file_ids_to_update = [parent_file_id]
        with self.engine.db._get_connection() as conn:
            children = conn.execute("SELECT id FROM media_files WHERE parent_file_id = ?", (parent_file_id,)).fetchall()
            file_ids_to_update.extend([c['id'] for c in children])

        self.table.setUpdatesEnabled(False)
        for fid in file_ids_to_update:
            row_idx = -1
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 1)
                if item and item.data(Qt.UserRole) == fid:
                    row_idx = row
                    break
            if row_idx != -1:
                file_data = self.engine.db.get_file_by_id(fid)
                if not file_data: continue

                # 1. Update Status Column
                status = file_data.get('match_status', 'pending').upper()
                if file_data.get('category') != 'video':
                    status = 'LINKED' if file_data.get('parent_file_id') else 'ORPHANED'
                
                status_item = self.table.item(row_idx, 0)
                if status_item:
                    status_item.setData(Qt.UserRole, status)
                    status_item.setText(status)
                    widget = self.table.cellWidget(row_idx, 0)
                    if widget:
                        sc = Theme.STATUS_COLORS.get(status, '#64748B')
                        widget.setText(status)
                        widget.setStyleSheet(f"color: {sc}; background: transparent; font-weight: 700; font-size: 11px;")

                # 2. Update New Name Preview Column
                new_name = self.engine.formatter.generate_name(fid, self.engine.config.settings)
                if new_name:
                    import os
                    ext = os.path.splitext(file_data.get('file_name', ''))[1]
                    preview = f"{new_name}{ext}"
                else:
                    preview = "-"
                self.table.setItem(row_idx, 3, QTableWidgetItem(preview))
                
        self.table.setUpdatesEnabled(True)

    def _on_item_double_clicked(self, item):
        row = item.row()
        item_with_id = self.table.item(row, 1)
        if not item_with_id: return
        file_id = item_with_id.data(Qt.UserRole)
        file_data = self.engine.db.get_file_by_id(file_id)
        
        if not file_data: return

        dialog = ManualResolveDialog(self.engine, file_data, self)
        if dialog.exec():
            # Refresh only the affected rows instantly
            self._update_rows_natively(file_id)
            self._on_selection_changed()

    def _on_manual_fix_clicked(self, vid):
        """Opens the Manual Resolve dialog for a specific file."""
        dialog = ManualResolveDialog(self.engine, vid, self)
        if dialog.exec():
            # Refresh only the affected rows instantly
            self._update_rows_natively(vid['id'])
            self._on_selection_changed()

    def _on_rename_all_clicked(self):
        """Creates a plan and executes the renaming process."""
        self.rename_all_btn.setEnabled(False)
        self.status_info.setText("Analyzing files and generating plan...")
        self.status_info.show()
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0) # Indeterminate
        
        self.plan_worker = PlanWorker(self.engine)
        self.active_workers.append(self.plan_worker)
        self.plan_worker.plan_ready.connect(self._on_plan_ready)
        self.plan_worker.error.connect(self._on_plan_error)
        self.plan_worker.finished.connect(self.plan_worker.deleteLater)
        self.plan_worker.start()

    def _on_plan_ready(self, plan):
        self.rename_all_btn.setEnabled(True)
        self.status_info.hide()
        self.progress_bar.hide()
        
        # Filter for renames
        renames = [p for p in plan if p['action'] in ('rename', 'delete')]
        if not renames:
            QMessageBox.information(self, "Rename", "No files need renaming or all are already up to date.")
            return
            
        # 2. Confirm with user
        dialog = PreviewDialog(renames, self)
        if dialog.exec() == QDialog.Accepted:
            self._execute_rename_plan(renames)

    def _on_plan_error(self, error_msg):
        self.rename_all_btn.setEnabled(True)
        self.status_info.hide()
        self.progress_bar.hide()
        QMessageBox.critical(self, "Plan Error", f"Failed to generate rename plan: {error_msg}")

    def _execute_rename_plan(self, plan):
        # 3. Start Worker
        self.rename_all_btn.setEnabled(False)
        self.status_info.setText("Executing renames...")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(10)
        
        self.rename_worker = RenameWorker(self.engine, plan)
        self.active_workers.append(self.rename_worker)
        self.rename_worker.finished.connect(self._on_rename_finished)
        self.rename_worker.finished.connect(self.rename_worker.deleteLater)
        self.rename_worker.start()

    def _on_rename_finished(self, results):
        self.rename_all_btn.setEnabled(True)
        self.status_info.hide()
        self.progress_bar.hide()
        
        summary = (f"Renaming Complete!\n\n"
                   f"✅ Success: {results['success']}\n"
                   f"🗑️ Deleted: {results['deleted']}\n"
                   f"⚠️ Failed: {results['failed']}\n"
                   f"⏭️ Skipped: {results['skipped']}")
        
        if results['failed'] > 0:
            summary += "\n\nCheck logs for details on failures."
            
        QMessageBox.information(self, "Rename Results", summary)
        self.refresh_data()

    def _on_open_folder(self, file_path):
        """Opens the system file explorer at the file's location."""
        import os
        folder = os.path.dirname(file_path)
        if os.path.exists(folder):
            if os.name == 'nt':
                os.startfile(folder)
            else:
                import subprocess
                import sys
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.call([opener, folder])

    def _on_filter_btn_clicked(self, clicked_btn):
        # Enforce single selection style logic manually
        for btn in self.filter_btns:
            if btn != clicked_btn:
                btn.blockSignals(True)
                btn.setChecked(False)
                btn.blockSignals(False)
            else:
                btn.setChecked(True) # Prevent unchecking the active one
                self.current_filter = btn.property("filter_val")
                
        # Update batch action button based on context
        try:
            self.batch_ignore_btn.clicked.disconnect()
        except: pass
        
        if self.current_filter == "ignored":
            self.batch_ignore_btn.setText("↩️ Restore Selected")
            self.batch_ignore_btn.setStyleSheet(f"""
                QPushButton {{ background: {Theme.SUCCESS}; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; border: none; }}
                QPushButton:hover {{ background: #059669; }}
            """)
            self.batch_ignore_btn.clicked.connect(self._restore_selected)
        else:
            self.batch_ignore_btn.setText("🗑 Ignore Selected")
            self.batch_ignore_btn.setStyleSheet(f"""
                QPushButton {{ background: {Theme.ERROR}; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; border: none; }}
                QPushButton:hover {{ background: #DC2626; }}
            """)
            self.batch_ignore_btn.clicked.connect(self._ignore_selected)
                
        self._apply_filters()
        self.table.clearSelection()

    def _apply_filters(self):
        """Filters the table rows based on the search text and button filter."""
        search_text = self.filter_input.text().lower()
        
        for row in range(self.table.rowCount()):
            # 1. Evaluate Text Search Match
            text_match = False
            if not search_text:
                text_match = True
            else:
                for col in range(4):
                    item = self.table.item(row, col)
                    if item:
                        if search_text in item.text().lower():
                            text_match = True
                            break
                        role_data = item.data(Qt.UserRole)
                        if isinstance(role_data, str) and search_text in role_data.lower():
                            text_match = True
                            break
                            
            # 2. Evaluate Button Filter Match
            btn_match = False
            status_item = self.table.item(row, 0)
            type_item = self.table.item(row, 2)
            
            if status_item and type_item:
                status = status_item.data(Qt.UserRole)
                media_type = type_item.text()
                
                if self.current_filter == "ignored":
                    if status == 'IGNORED':
                        btn_match = True
                else:
                    if status == 'IGNORED':
                        btn_match = False
                    elif self.current_filter == "all":
                        btn_match = True
                    elif self.current_filter == "review":
                        # Pending, multiple, uncertain, no_match
                        if status in ('PENDING', 'MULTIPLE', 'UNCERTAIN', 'NO_MATCH'):
                            btn_match = True
                    elif self.current_filter == "movies":
                        if status == 'MATCHED' and media_type == "Movie":
                            btn_match = True
                    elif self.current_filter == "shows":
                        if status == 'MATCHED' and media_type == "TV Show":
                            btn_match = True
                    elif self.current_filter == "extras":
                        raw_cat = type_item.data(Qt.UserRole)
                        if raw_cat != 'video':
                            btn_match = True

            # Show row only if BOTH match
            self.table.setRowHidden(row, not (text_match and btn_match))

    def _on_selection_changed(self):
        selected_items = self.table.selectedItems()
        self._update_batch_bar()
        
        if not selected_items:
            self.inspector.set_empty()
            return
            
        selected_rows = set(i.row() for i in selected_items)
        if len(selected_rows) > 1:
            self.inspector.set_empty()
            self.inspector.title_label.setText(f"{len(selected_rows)} files selected")
            self.inspector.plot_label.setText("Batch editing is available via the floating action bar.")
            return

        # Row 1 (Original Name) has the file_id in UserRole
        row = selected_items[0].row()
        item_with_id = self.table.item(row, 1)
        if not item_with_id: return
        file_id = item_with_id.data(Qt.UserRole)
        
        # Get file data from DB
        file_data = self.engine.db.get_file_by_id(file_id)
        if not file_data:
            return

        # Update technical info regardless of status
        self.inspector.update_tech_info(file_data)

        # Fetch links for this file
        links = self.engine.db.get_links_for_file(file_id)
        media_item_id = links[0]['media_item_id'] if links else None

        # If matched, get media item details
        if file_data['match_status'] in ('matched', 'uncertain') and media_item_id:
            media_item = self.engine.db.get_media_item_by_id(media_item_id)
            if media_item:
                import json
                self.inspector.update_from_data(media_item, candidates=None)
                
                # Load poster if exists
                if media_item['poster_path']:
                    self._load_poster(media_item['poster_path'])
        
        elif file_data['match_status'] == 'multiple':
            # Show file name and multiple found message
            self.inspector.update_from_data({'title': file_data['file_name'], 'overview': 'Multiple potential matches found for this file. Please use the "Fix" button to choose the correct one.'}, candidates=None)
            self.inspector.poster_label.clear()
        else:
            self.inspector.set_empty()
            self.inspector.update_tech_info(file_data) # Re-fill tech info after set_empty
            self.inspector.title_label.setText(file_data['file_name'])
            self.inspector.plot_label.setText("No identification found yet. Use manual fix if needed.")
            self.inspector.poster_label.clear()
            self.inspector.poster_label.clear()

    def _update_batch_bar(self):
        selected_items = self.table.selectedItems()
        # In a SelectRows mode, each cell is considered "selected".
        # So we count the unique rows.
        selected_rows = set(item.row() for item in selected_items if not self.table.isRowHidden(item.row()))
        checked_count = len(selected_rows)
                
        if checked_count > 1:
            self.batch_count_lbl.setText(f"{checked_count} files selected")
            self.batch_bar.show()
        else:
            self.batch_bar.hide()
            
    def _deselect_all(self):
        self.table.clearSelection()
        
    def _ignore_selected(self):
        # Collect IDs to ignore
        ids_to_ignore = []
        selected_items = self.table.selectedItems()
        selected_rows = set(item.row() for item in selected_items if not self.table.isRowHidden(item.row()))
        
        for row in selected_rows:
            item_with_id = self.table.item(row, 1)
            if item_with_id:
                ids_to_ignore.append(item_with_id.data(Qt.UserRole))
                    
        if not ids_to_ignore: return
        
        with self.engine.db._get_connection() as conn:
            for file_id in ids_to_ignore:
                conn.execute("UPDATE media_files SET match_status = 'IGNORED' WHERE id = ?", (file_id,))
                
        # Instantly remove rows from UI for performance
        self.table.setUpdatesEnabled(False)
        for row in sorted(list(selected_rows), reverse=True):
            self.table.removeRow(row)
        self.table.setUpdatesEnabled(True)
        
        self.table.clearSelection()
        self.stats_label.setText(f"{self.table.rowCount()} files found")

    def _restore_selected(self):
        # Collect IDs to restore
        ids_to_restore = []
        selected_items = self.table.selectedItems()
        selected_rows = set(item.row() for item in selected_items if not self.table.isRowHidden(item.row()))
        
        for row in selected_rows:
            item_with_id = self.table.item(row, 1)
            if item_with_id:
                ids_to_restore.append((row, item_with_id.data(Qt.UserRole)))
                    
        if not ids_to_restore: return
        
        with self.engine.db._get_connection() as conn:
            self.table.setUpdatesEnabled(False)
            for row, file_id in ids_to_restore:
                # Smart restore: figure out what status it should be
                link = conn.execute("SELECT id FROM file_media_links WHERE file_id = ?", (file_id,)).fetchone()
                if link:
                    new_status = 'matched'
                else:
                    candidate = conn.execute("SELECT id FROM match_candidates WHERE file_id = ?", (file_id,)).fetchone()
                    new_status = 'multiple' if candidate else 'pending'
                    
                conn.execute("UPDATE media_files SET match_status = ? WHERE id = ?", (new_status, file_id))
                
                # Update UI natively
                status_item = self.table.item(row, 0)
                if status_item:
                    display_status = new_status.upper()
                    status_item.setData(Qt.UserRole, display_status)
                    status_item.setText(display_status)
                    status_label = self.table.cellWidget(row, 0)
                    if status_label:
                        sc = Theme.STATUS_COLORS.get(display_status, '#64748B')
                        status_label.setText(display_status)
                        status_label.setStyleSheet(f"color: {sc}; background: transparent; font-weight: 700; font-size: 11px;")
            self.table.setUpdatesEnabled(True)
        
        self.table.clearSelection()
        self._apply_filters()
        self.stats_label.setText(f"{self.table.rowCount()} files found")

    def _on_data_loaded(self, videos, poster_paths=None):
        """Populates the table and starts prefetching posters."""
        if not videos:
            self.table.setRowCount(0)
            self.stats_label.setText("0 files found")
            return

        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)

        try:
            self.table.setRowCount(len(videos))
            self.stats_label.setText(f"{len(videos)} files found")

            # Use centralized Theme constants
            status_colors = Theme.STATUS_COLORS
            btn_style = Theme.get_action_button_style()

            for i, vid in enumerate(videos):
                # 3. Type
                raw_cat = vid.get('category') or 'video'
                if raw_cat == 'video':
                    sub_cat = vid.get('sub_category') or vid.get('fn_media_type') or 'movie'
                    cat_display = "TV Show" if sub_cat in ('tv', 'episode') else "Movie"
                elif raw_cat == 'extra':
                    cat_display = "Bonus Video"
                else:
                    cat_display = raw_cat.capitalize()
                    
                # 0. Status (colored text)
                status = vid.get('match_status', 'pending').upper()
                if raw_cat != 'video':
                    status = 'LINKED' if vid.get('parent_file_id') else 'ORPHANED'

                sc = status_colors.get(status, '#64748B')

                status_label = QLabel(status)
                status_label.setAlignment(Qt.AlignCenter)
                status_label.setStyleSheet(f"color: {sc}; background: transparent; font-weight: 700; font-size: 11px;")
                self.table.setCellWidget(i, 0, status_label)

                # Set text for sorting, but make it transparent so the QLabel shows cleanly
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QColor(0, 0, 0, 0))
                status_item.setData(Qt.UserRole, status)
                self.table.setItem(i, 0, status_item)

                # 1. Original Name
                name_item = QTableWidgetItem(vid['file_name'])
                name_item.setData(Qt.UserRole, vid['id'])
                self.table.setItem(i, 1, name_item)
                
                # 2. Type
                type_item = QTableWidgetItem(cat_display)
                type_item.setData(Qt.UserRole, raw_cat)
                self.table.setItem(i, 2, type_item)

                # 3. New Name Preview
                ident_text = vid.get('_new_name') or "-"
                if raw_cat != 'video' and not vid.get('_new_name'):
                    parent_id = vid.get('parent_file_id')
                    if parent_id:
                        parent_file = self.engine.db.get_file_by_id(parent_id)
                        if parent_file:
                            ident_text = f"Parent: {parent_file.get('file_name', 'Unknown')}"
                self.table.setItem(i, 3, QTableWidgetItem(ident_text))

                # 5. Actions
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(8, 2, 8, 2)
                actions_layout.setSpacing(8)

                edit_btn = QPushButton("Fix")
                edit_btn.setFixedSize(55, 24)
                edit_btn.setCursor(Qt.PointingHandCursor)
                edit_btn.setStyleSheet(btn_style)
                edit_btn.clicked.connect(lambda checked=False, v=vid: self._on_manual_fix_clicked(v))

                folder_btn = QPushButton("Open")
                folder_btn.setFixedSize(55, 24)
                folder_btn.setCursor(Qt.PointingHandCursor)
                folder_btn.setStyleSheet(btn_style)
                folder_btn.clicked.connect(lambda checked=False, p=vid['current_path']: self._on_open_folder(p))

                if status == 'IGNORED':
                    del_btn = QPushButton("↩️")
                    del_btn.setFixedSize(28, 24)
                    del_btn.setCursor(Qt.PointingHandCursor)
                    del_btn.setToolTip("Restore this file")
                    del_btn.setStyleSheet(f"""
                        QPushButton {{ background: transparent; color: {Theme.SUCCESS}; font-size: 14px; border-radius: 4px; }}
                        QPushButton:hover {{ background: rgba(16, 185, 129, 0.1); }}
                    """)
                    del_btn.clicked.connect(lambda checked=False, f_id=vid['id'], r=i: self._restore_file(f_id, r))
                else:
                    del_btn = QPushButton("🗑")
                    del_btn.setFixedSize(28, 24)
                    del_btn.setCursor(Qt.PointingHandCursor)
                    del_btn.setToolTip("Ignore this file")
                    del_btn.setStyleSheet(f"""
                        QPushButton {{ background: transparent; color: {Theme.ERROR}; font-size: 14px; border-radius: 4px; }}
                        QPushButton:hover {{ background: rgba(239, 68, 68, 0.1); }}
                    """)
                    del_btn.clicked.connect(lambda checked=False, f_id=vid['id']: self._ignore_file(f_id))

                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(folder_btn)
                actions_layout.addWidget(del_btn)
                actions_widget.setStyleSheet("background: transparent;")
                self.table.setCellWidget(i, 4, actions_widget)

                # Keep UI alive — every 10 rows
                if i % 10 == 0:
                    QApplication.processEvents()

            # Update Stats and visibility
            has_matches = any(v.get('match_status') == 'matched' for v in videos)
            if has_matches:
                self.rename_all_btn.show()
            else:
                self.rename_all_btn.hide()

            # Start prefetching posters in background (paths already collected by DataLoader)
            if poster_paths:
                self._start_prefetch(poster_paths)

        finally:
            self.table.setSortingEnabled(True)
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)
            self._update_batch_bar()

    def _ignore_file(self, file_id):
        """Sets the file's status to IGNORED so it is hidden from the UI and skipped by the pipeline."""
        with self.engine.db._get_connection() as conn:
            conn.execute("UPDATE media_files SET match_status = 'IGNORED' WHERE id = ?", (file_id,))
            
        # Find row and remove it instantly
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item and item.data(Qt.UserRole) == file_id:
                self.table.removeRow(row)
                break
                
        self.table.clearSelection()
        self.stats_label.setText(f"{self.table.rowCount()} files found")

    def _restore_file(self, file_id, row):
        """Restores an ignored file back to its correct state."""
        with self.engine.db._get_connection() as conn:
            # Smart restore: figure out what status it should be
            link = conn.execute("SELECT id FROM file_media_links WHERE file_id = ?", (file_id,)).fetchone()
            if link:
                new_status = 'matched'
            else:
                candidate = conn.execute("SELECT id FROM match_candidates WHERE file_id = ?", (file_id,)).fetchone()
                new_status = 'multiple' if candidate else 'pending'
                
            conn.execute("UPDATE media_files SET match_status = ? WHERE id = ?", (new_status, file_id))
            
        status_item = self.table.item(row, 0)
        if status_item:
            display_status = new_status.upper()
            status_item.setData(Qt.UserRole, display_status)
            status_item.setText(display_status)
            status_label = self.table.cellWidget(row, 0)
            if status_label:
                sc = Theme.STATUS_COLORS.get(display_status, '#64748B')
                status_label.setText(display_status)
                status_label.setStyleSheet(f"color: {sc}; background: transparent; font-weight: 700; font-size: 11px;")
                
        self.table.clearSelection()
        self._apply_filters()
        self.stats_label.setText(f"{self.table.rowCount()} files found")

    def _load_poster(self, poster_path):
        """Asynchronously load poster image, with sync check for local cache."""
        if not poster_path:
            self.inspector.poster_label.setText("No Poster")
            return

        # Correct root path
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        cache_dir = os.path.join(root, 'data', 'cache', 'posters')
        file_name = poster_path.lstrip('/')
        local_path = os.path.join(cache_dir, file_name)

        # 1. Sync check: If it's already on disk, show it immediately
        if os.path.exists(local_path):
            pixmap = QPixmap(local_path)
            if not pixmap.isNull():
                self._on_poster_loaded(pixmap)
                return

        # 2. Async download: Only if not in cache
        if self.poster_worker and self.poster_worker.isRunning():
            try: self.poster_worker.finished.disconnect(self._on_poster_loaded)
            except: pass
            self.active_workers.append(self.poster_worker) # Keep it alive

        from ui.v3.components.image_loader import ImageDownloader
        url = f"https://image.tmdb.org/t/p/w500{poster_path}"
        self.poster_worker = ImageDownloader(url, local_path, session=self.engine.resolver.api.session)
        self.active_workers.append(self.poster_worker)
        self.poster_worker.finished.connect(self._on_poster_loaded)
        self.poster_worker.finished.connect(self.poster_worker.deleteLater)
        self.poster_worker.start()

    def _cleanup_worker(self, worker):
        """Removes finished workers from the active list."""
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        if worker == self.loader:
            self.loader = None
        if worker == self.poster_worker:
            self.poster_worker = None
        if hasattr(self, 'rename_worker') and worker == self.rename_worker:
            self.rename_worker = None

    def _on_poster_loaded(self, pixmap):
        if not pixmap.isNull():
            scaled = pixmap.scaled(self.inspector.poster_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.inspector.poster_label.setPixmap(scaled)
        else:
            self.inspector.poster_label.setText("No Poster")

    def refresh_data(self):
        """Triggers background data loading."""
        # 1. Cleanup old loader safely
        try:
            if self.loader and self.loader.isRunning():
                try: self.loader.data_ready.disconnect(self._on_data_loaded)
                except: pass
                self.active_workers.append(self.loader)
        except RuntimeError:
            self.loader = None

        self.loader = DataLoader(self.engine)
        self.active_workers.append(self.loader)
        self.loader.data_ready.connect(self._on_data_loaded)
        self.loader.finished.connect(self.loader.deleteLater)
        self.loader.finished.connect(lambda: self._set_loader_none())
        self.loader.start()

    def _set_loader_none(self):
        self.loader = None

    def _start_prefetch(self, paths):
        """Starts a background worker to download all posters in the list."""
        try:
            if hasattr(self, 'prefetcher') and self.prefetcher and self.prefetcher.isRunning():
                return
        except RuntimeError:
            self.prefetcher = None
            
        class PrefetchWorker(QThread):
            def __init__(self, paths, root, session):
                super().__init__()
                self.paths = paths
                self.root = root
                self.session = session
            def run(self):
                cache_dir = os.path.join(self.root, 'data', 'cache', 'posters')
                for p in self.paths:
                    local = os.path.join(cache_dir, p.lstrip('/'))
                    if not os.path.exists(local):
                        url = f"https://image.tmdb.org/t/p/w500{p}"
                        try:
                            r = self.session.get(url, timeout=5)
                            if r.status_code == 200:
                                os.makedirs(os.path.dirname(local), exist_ok=True)
                                with open(local, 'wb') as f:
                                    f.write(r.content)
                        except: pass

        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.prefetcher = PrefetchWorker(paths, root, self.engine.resolver.api.session)
        self.active_workers.append(self.prefetcher)
        self.prefetcher.finished.connect(self.prefetcher.deleteLater)
        self.prefetcher.start()
