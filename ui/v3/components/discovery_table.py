import os
from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QWidget, QHBoxLayout, QPushButton, QApplication, QStyledItemDelegate, QStyle, QMenu)
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPalette
from PySide6.QtCore import Qt, QSize, QRect, Signal, Slot
from ui.v3.styles.theme import Theme
from core.i18n import T

class PremiumDelegate(QStyledItemDelegate):
    """Custom delegate to draw premium row selection with a left accent bar."""
    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw Row Background
        if option.state & QStyle.State_Selected:
            grad = QLinearGradient(option.rect.topLeft(), option.rect.topRight())
            grad.setColorAt(0, QColor(Theme.PRIMARY))
            grad.setColorAt(0.005, QColor(Theme.PRIMARY))
            grad.setColorAt(0.007, QColor(Theme.SURFACE_LIGHT))
            grad.setColorAt(1.0, QColor(Theme.SURFACE_DARK))
            painter.fillRect(option.rect, grad)
            
            accent_rect = QRect(option.rect.left(), option.rect.top(), 4, option.rect.height())
            painter.fillRect(accent_rect, QColor(Theme.PRIMARY))
        else:
            if option.state & QStyle.State_MouseOver:
                painter.fillRect(option.rect, QColor(Theme.SURFACE_LIGHT + "40"))

        # Group Separator for Conflicts
        is_group_start = index.data(Qt.UserRole + 1)
        if is_group_start:
            painter.setPen(QColor(Theme.BORDER))
            # Draw a subtle line at the top
            painter.drawLine(option.rect.left() + 10, option.rect.top(), option.rect.right() - 10, option.rect.top())

        painter.restore()
        if index.column() != 0:
            super().paint(painter, option, index)

class DiscoveryTable(QTableWidget):
    """Handles all table operations: rendering rows, cell widgets, and filtering."""
    
    fix_requested = Signal(dict)
    manual_edit_requested = Signal(dict)
    open_folder_requested = Signal(str)
    clear_match_requested = Signal(int)
    ignore_requested = Signal(int)
    batch_ignore_requested = Signal()
    batch_identify_requested = Signal()
    batch_edit_requested = Signal()
    fetch_language_requested = Signal(list) # item_ids
    restore_requested = Signal(int, int) # file_id, row

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_setup()

    def _init_setup(self):
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels([
            T("discovery.table.status"), 
            T("discovery.table.original_name"), 
            T("discovery.table.type"), 
            T("discovery.table.new_name"), 
            T("discovery.table.actions")
        ])
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSelectionMode(QTableWidget.ExtendedSelection)
        self.verticalHeader().setVisible(False)
        
        # Style
        self.setItemDelegate(PremiumDelegate(self))
        self.setStyleSheet(Theme.get_discovery_table_style())
        
        pal = self.palette()
        pal.setColor(QPalette.Highlight, QColor(0, 0, 0, 0))
        pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(pal)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, 100)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.setColumnWidth(2, 100)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.setColumnWidth(4, 300) # Maximum spacious width
        header.setDefaultAlignment(Qt.AlignLeft)
        self.verticalHeader().setDefaultSectionSize(72) # Maximum 72px row height
        
        # Enable Context Menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu_requested)

    def _on_context_menu_requested(self, pos):
        self._show_actions_menu(self.viewport().mapToGlobal(pos))

    def fill_data(self, videos, is_conflicts=False):
        self.setUpdatesEnabled(False)
        self.setSortingEnabled(False)
        self.clearContents()
        self.setRowCount(len(videos))
        
        prev_name = None
        for i, vid in enumerate(videos):
            try:
                curr_name = vid.get('_new_name')
                is_new_group = is_conflicts and i > 0 and curr_name != prev_name
                prev_name = curr_name

                status = vid.get('match_status', 'pending').upper()
                if vid.get('_is_conflict'):
                    status = 'CONFLICT'
                    
                raw_cat = vid.get('category', 'unknown') or 'unknown'
                
                if raw_cat != 'video':
                    if status not in ('CONFLICT', 'IGNORED'):
                        status = 'LINKED' if vid.get('parent_file_id') else 'ORPHANED'
                
                # 0. Status
                sc = Theme.STATUS_COLORS.get(status, '#64748B')
                status_label = QLabel(status)
                status_label.setAlignment(Qt.AlignCenter)
                status_label.setStyleSheet(Theme.get_status_label_style(color=sc))
                self.setCellWidget(i, 0, status_label)
                
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QColor(0, 0, 0, 0))
                status_item.setData(Qt.UserRole, status)
                if is_new_group:
                    status_item.setData(Qt.UserRole + 1, True) # Mark for delegate
                self.setItem(i, 0, status_item)

                # 1. Original Name
                name_item = QTableWidgetItem(vid.get('file_name', T("common.unknown")))
                name_item.setData(Qt.UserRole, vid['id'])
                name_item.setData(Qt.UserRole + 3, vid.get('current_path')) # Store path for context menu
                if is_new_group:
                    name_item.setData(Qt.UserRole + 1, True)
                self.setItem(i, 1, name_item)
                
                # 2. Type
                mtype = vid.get('_media_type_from_db') or vid.get('fn_media_type')
                sub_cat = vid.get('sub_category')
                
                cat_display = self._get_type_display(raw_cat, mtype, sub_cat)
                
                type_item = QTableWidgetItem(cat_display)
                type_item.setData(Qt.UserRole, raw_cat)
                type_item.setData(Qt.UserRole + 2, mtype)
                if is_new_group:
                    type_item.setData(Qt.UserRole + 1, True)
                self.setItem(i, 2, type_item)

                # 3. New Name Preview
                ident_text = vid.get('_new_name') or "-"
                preview_item = QTableWidgetItem(ident_text)
                if is_new_group:
                    preview_item.setData(Qt.UserRole + 1, True)
                self.setItem(i, 3, preview_item)

                # 4. Actions
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(8, 8, 8, 8)
                actions_layout.setSpacing(10)

                # --- 1. Primary Action Button ---
                primary_btn = None
                if status == 'IGNORED':
                    # Restore Button for Trash
                    primary_btn = QPushButton()
                    primary_btn.setIcon(Theme.get_icon("refresh", size=20, color=Theme.TEXT_MAIN))
                    primary_btn.setToolTip(T("discovery.actions.restore"))
                    primary_btn.setFixedSize(54, 46)
                    primary_btn.setCursor(Qt.PointingHandCursor)
                    primary_btn.setStyleSheet(Theme.get_discovery_action_btn_style('success'))
                    primary_btn.clicked.connect(lambda checked=False, fid=vid['id']: self.restore_requested.emit(fid, i))
                elif raw_cat == 'video':
                    # API Resolve Button (Only for videos)
                    primary_btn = QPushButton()
                    primary_btn.setIcon(Theme.get_icon("wand", size=20, color=Theme.TEXT_MAIN))
                    primary_btn.setToolTip(T("discovery.actions.fix"))
                    primary_btn.setFixedSize(54, 46)
                    primary_btn.setCursor(Qt.PointingHandCursor)
                    variant = 'danger' if status == 'CONFLICT' else 'neutral'
                    primary_btn.setStyleSheet(Theme.get_discovery_action_btn_style(variant))
                    primary_btn.clicked.connect(lambda checked=False, v=vid: self.fix_requested.emit(v))
                
                if status == 'IGNORED':
                    # Special Trash View: Just Restore and Open Folder, no Edit/Fix or Overflow
                    # 1. Restore
                    actions_layout.addWidget(primary_btn)
                    
                    # 2. Open Folder
                    open_btn = QPushButton()
                    open_btn.setIcon(Theme.get_icon("folder", size=20, color=Theme.TEXT_MAIN))
                    open_btn.setToolTip(T("discovery.actions.open_folder"))
                    open_btn.setFixedSize(54, 46)
                    open_btn.setCursor(Qt.PointingHandCursor)
                    open_btn.setStyleSheet(Theme.get_discovery_action_btn_style('neutral'))
                    open_btn.clicked.connect(lambda checked=False, p=vid['current_path']: self.open_folder_requested.emit(p))
                    actions_layout.addWidget(open_btn)
                else:
                    # Regular View logic
                    if primary_btn:
                        actions_layout.addWidget(primary_btn)
                    
                    # --- 2. Base Edit Button (Only for videos) ---
                    if raw_cat == 'video':
                        edit_btn = QPushButton()
                        edit_btn.setIcon(Theme.get_icon("pencil", size=20, color=Theme.TEXT_MAIN))
                        edit_btn.setToolTip(T("discovery.actions.edit"))
                        edit_btn.setFixedSize(54, 46)
                        edit_btn.setCursor(Qt.PointingHandCursor)
                        edit_btn.setStyleSheet(Theme.get_discovery_action_btn_style('neutral'))
                        edit_btn.clicked.connect(lambda checked=False, v=vid: self._on_manual_edit_clicked(v))
                        actions_layout.addWidget(edit_btn)

                    # --- 3. Overflow Menu (...) ---
                    overflow_btn = QPushButton()
                    overflow_btn.setIcon(Theme.get_icon("more-horizontal", size=20, color=Theme.TEXT_MAIN))
                    overflow_btn.setToolTip(T("common.more"))
                    overflow_btn.setFixedSize(54, 46)
                    overflow_btn.setCursor(Qt.PointingHandCursor)
                    overflow_btn.setStyleSheet(Theme.get_discovery_action_btn_style('neutral'))
                    overflow_btn.clicked.connect(lambda checked=False, b=overflow_btn, v=vid: self._show_row_menu(b, v))
                    actions_layout.addWidget(overflow_btn)

                actions_layout.addStretch()
                self.setCellWidget(i, 4, actions_widget)

            except Exception as row_err:
                import logging
                logging.getLogger(__name__).error(f"Error filling row {i}: {row_err}")

            if i % 10 == 0: QApplication.processEvents()

        self.setSortingEnabled(True)
        self.setUpdatesEnabled(True)

    def _on_manual_edit_clicked(self, vid):
        self.manual_edit_requested.emit(vid)

    def _show_row_menu(self, button, vid):
        """Shows the overflow menu for a specific row's button."""
        self._show_actions_menu(button.mapToGlobal(button.rect().bottomLeft()), vid, is_context=False)

    def _show_actions_menu(self, global_pos, vid=None, is_context=True):
        """Renders the overflow/context menu."""
        if not vid:
            # Try to get vid from current selection if not provided
            items = self.selectedItems()
            if not items: return
            row = items[0].row()
            file_id = self.item(row, 1).data(Qt.UserRole)
            status = self.item(row, 0).data(Qt.UserRole)
            raw_cat = self.item(row, 2).data(Qt.UserRole)
            path = self.item(row, 1).data(Qt.UserRole + 3) # Retrieve stored path
        else:
            file_id = vid['id']
            status = vid.get('match_status', 'pending').upper()
            raw_cat = vid.get('category', 'video')
            path = vid['current_path']

        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        # Apply a clean dark style to the menu
        menu.setStyleSheet(Theme.get_context_menu_style())
        
        if status == 'IGNORED':
            # Trash Context Menu: Minimal
            is_multi = len(set(item.row() for item in self.selectedItems())) > 1
            
            restore_act = menu.addAction(Theme.get_icon("refresh", size=16, color=Theme.TEXT_MAIN), T("discovery.actions.restore"))
            restore_act.triggered.connect(lambda: self.restore_requested.emit(file_id, 0))
            
            if not is_multi:
                menu.addSeparator()
                open_act = menu.addAction(Theme.get_icon("folder", size=16, color=Theme.TEXT_MAIN), T("discovery.actions.open_folder"))
                if path:
                    open_act.triggered.connect(lambda: self.open_folder_requested.emit(path))
                else:
                    open_act.setEnabled(False)
        else:
            # --- PRIMARY ACTIONS (Only shown in Right-Click context menu to avoid redundancy with row buttons) ---
            if is_context:
                is_multi = len(set(item.row() for item in self.selectedItems())) > 1
                
                # 1. API Fix / Identify
                if raw_cat == 'video':
                    label = T("discovery.actions.batch_identify") if is_multi else T("discovery.actions.fix")
                    icon_name = "wand"
                    fix_act = menu.addAction(Theme.get_icon(icon_name, size=16, color=Theme.TEXT_MAIN), label)
                    
                    if is_multi:
                        fix_act.triggered.connect(self.batch_identify_requested.emit)
                    elif vid:
                        fix_act.triggered.connect(lambda: self.fix_requested.emit(vid))
                    else:
                        # Try to find vid from selected row
                        fix_act.triggered.connect(lambda: self.fix_requested.emit({'id': file_id, 'category': 'video'}))
                
                # 2. Manual Edit (For all)
                edit_label = T("discovery.actions.batch_actions") if is_multi else T("discovery.actions.edit")
                edit_icon = "wand" if is_multi else "pencil"
                edit_act = menu.addAction(Theme.get_icon(edit_icon, size=16, color=Theme.TEXT_MAIN), edit_label)
                
                if is_multi:
                    edit_act.triggered.connect(self.batch_edit_requested.emit)
                elif vid:
                    edit_act.triggered.connect(lambda: self._on_manual_edit_clicked(vid))
                else:
                    edit_act.triggered.connect(lambda: self._on_manual_edit_clicked({'id': file_id}))
                
                menu.addSeparator()

            # 3. Folder Action
            open_act = menu.addAction(Theme.get_icon("folder", size=16, color=Theme.TEXT_MAIN), T("discovery.actions.open_folder"))
            if path:
                open_act.triggered.connect(lambda: self.open_folder_requested.emit(path))
            else:
                open_act.setEnabled(False)
                
            # 4. Fetch Missing Language Action (Only for videos)
            if raw_cat == 'video':
                fetch_lang_act = menu.addAction(Theme.get_icon("globe", size=16, color=Theme.TEXT_MAIN), T("discovery.batch.fetch_language") if "discovery.batch.fetch_language" != T("discovery.batch.fetch_language") else "Fetch Missing Language")
                fetch_lang_act.triggered.connect(lambda: self.fetch_language_requested.emit(self.get_selected_ids()))
            
            # 5. Clear Match Action (Only for videos)
            if raw_cat == 'video':
                clear_act = menu.addAction(Theme.get_icon("refresh", size=16, color=Theme.TEXT_MAIN), T("discovery.actions.clear_match"))
                clear_act.setEnabled(status == 'MATCHED')
                clear_act.triggered.connect(lambda: self.clear_match_requested.emit(file_id))
            
            menu.addSeparator()
            
            # 5. Ignore Action
            ignore_act = menu.addAction(Theme.get_icon("trash-2", size=16, color=Theme.TEXT_MAIN), T("discovery.actions.ignore"))
            ignore_act.triggered.connect(lambda: self.ignore_requested.emit(file_id))
        
        menu.exec(global_pos)

    def apply_filters(self, current_filter, search_text):
        search_text = search_text.lower()
        for row in range(self.rowCount()):
            text_match = not search_text
            if search_text:
                for col in range(5):
                    item = self.item(row, col)
                    if item and (search_text in item.text().lower() or (isinstance(item.data(Qt.UserRole), str) and search_text in item.data(Qt.UserRole).lower())):
                        text_match = True
                        break
            
            btn_match = False
            status_item = self.item(row, 0)
            type_item = self.item(row, 2)
            if status_item and type_item:
                status = status_item.data(Qt.UserRole)
                raw_cat = type_item.data(Qt.UserRole)
                mtype = type_item.data(Qt.UserRole + 2)

                if current_filter == "ignored": btn_match = (status == 'IGNORED')
                else:
                    if status == 'IGNORED': btn_match = False
                    elif current_filter == "all": btn_match = True
                    elif current_filter == "review": btn_match = (status in ('PENDING', 'MULTIPLE', 'UNCERTAIN', 'NO_MATCH'))
                    elif current_filter == "conflicts": btn_match = (status == 'CONFLICT')
                    elif current_filter == "movies": btn_match = (status == 'MATCHED' and mtype == "movie")
                    elif current_filter == "shows": btn_match = (status == 'MATCHED' and mtype == "tv")
                    elif current_filter == "extras": btn_match = (raw_cat != 'video')
                    # Sub-filters for Extras
                    elif current_filter in ("subtitle", "image", "metadata", "extra"):
                        btn_match = (raw_cat == current_filter)

            self.setRowHidden(row, not (text_match and btn_match))

    def update_row_natively(self, file_id, file_data, engine):
        for row in range(self.rowCount()):
            item = self.item(row, 1)
            if item and item.data(Qt.UserRole) == file_id:
                # Update Status
                status = file_data.get('match_status', 'pending').upper()
                if file_data.get('category') != 'video':
                    if status not in ('CONFLICT', 'IGNORED'):
                        status = 'LINKED' if file_data.get('parent_file_id') else 'ORPHANED'
                
                status_item = self.item(row, 0)
                if status_item:
                    status_item.setData(Qt.UserRole, status)
                    status_item.setText(status)
                    widget = self.cellWidget(row, 0)
                    if widget:
                        sc = Theme.STATUS_COLORS.get(status, '#64748B')
                        widget.setText(status)
                        widget.setStyleSheet(Theme.get_status_label_style(color=sc))

                # Update Type
                links = engine.db.get_links_for_file(file_id)
                if links:
                    media = engine.db.get_media_item_by_id(links[0]['media_item_id'])
                    if media:
                        mtype = media.get('media_type')
                        raw_cat = file_data.get('category', 'video')
                        sub_cat = file_data.get('sub_category')
                        display = self._get_type_display(raw_cat, mtype, sub_cat)
                        self.setItem(row, 2, QTableWidgetItem(display))

                # Update Preview
                new_name = engine.formatter.generate_name(file_id, engine.config.settings)
                preview = f"{new_name}{os.path.splitext(file_data.get('file_name', ''))[1]}" if new_name else "-"
                self.setItem(row, 3, QTableWidgetItem(preview))
                break

    def _get_type_display(self, raw_cat, mtype, sub_cat):
        if raw_cat == 'video':
            return T("common.types.movie") if mtype == 'movie' else T("common.types.tv") if mtype == 'tv' else T("common.types.video")
        
        # Generic lookup for other categories (extra, subtitle, image, meta)
        cat_display = T(f"discovery.batch_operations.options.categories.{raw_cat}")
        if cat_display == f"discovery.batch_operations.options.categories.{raw_cat}":
            cat_display = raw_cat.capitalize()
        
        if sub_cat and sub_cat != raw_cat:
            sub_display = T(f"discovery.extras.subtypes.{sub_cat}")
            if sub_display == f"discovery.extras.subtypes.{sub_cat}":
                sub_display = sub_cat.title()
            return f"{cat_display} ({sub_display})"
        
        return cat_display

    def get_selected_ids(self):
        """Returns unique database IDs for all selected rows that are VISIBLE."""
        ids = []
        for item in self.selectedItems():
            row = item.row()
            if self.isRowHidden(row):
                continue
                
            # ID is stored in the UserRole of column 1
            if item.column() == 1:
                fid = item.data(Qt.UserRole)
                if fid: ids.append(fid)
        return list(set(ids))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            if self.selectedItems():
                self.batch_ignore_requested.emit()
        elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
            self.selectAll()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        """Triggers the context menu on right click."""
        item = self.itemAt(event.pos())
        if item:
            self._show_actions_menu(event.globalPos(), is_context=True)
