import os
from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QWidget, QHBoxLayout, QPushButton, QApplication, QStyledItemDelegate, QStyle)
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPalette
from PySide6.QtCore import Qt, QSize, QRect, Signal, Slot
from ui.v3.styles.theme import Theme

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

        painter.restore()
        if index.column() not in (0, 4):
            super().paint(painter, option, index)

class DiscoveryTable(QTableWidget):
    """Handles all table operations: rendering rows, cell widgets, and filtering."""
    
    fix_requested = Signal(dict)
    open_folder_requested = Signal(str)
    clear_match_requested = Signal(int)
    ignore_requested = Signal(int)
    restore_requested = Signal(int, int) # file_id, row

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_setup()

    def _init_setup(self):
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Status", "Original Name", "Type", "New Name Preview", "Actions"])
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.NoFocus)
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

    def fill_data(self, videos):
        self.setUpdatesEnabled(False)
        self.setSortingEnabled(False)
        self.clearContents()
        self.setRowCount(len(videos))
        
        for i, vid in enumerate(videos):
            try:
                status = vid.get('match_status', 'pending').upper()
                raw_cat = vid.get('category', 'unknown') or 'unknown'
                
                if raw_cat != 'video':
                    status = 'LINKED' if vid.get('parent_file_id') else 'ORPHANED'
                
                # 0. Status
                sc = Theme.STATUS_COLORS.get(status, '#64748B')
                status_label = QLabel(status)
                status_label.setAlignment(Qt.AlignCenter)
                status_label.setStyleSheet(f"color: {sc}; background: transparent; font-weight: 700; font-size: 11px;")
                self.setCellWidget(i, 0, status_label)
                
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QColor(0, 0, 0, 0))
                status_item.setData(Qt.UserRole, status)
                self.setItem(i, 0, status_item)

                # 1. Original Name
                name_item = QTableWidgetItem(vid.get('file_name', 'Unknown'))
                name_item.setData(Qt.UserRole, vid['id'])
                self.setItem(i, 1, name_item)
                
                # 2. Type
                mtype = vid.get('_media_type_from_db') or vid.get('fn_media_type')
                
                if raw_cat == 'video':
                    cat_display = "Movie" if mtype == 'movie' else "TV Show" if mtype == 'tv' else "Video"
                elif raw_cat == 'extra':
                    cat_display = "Bonus Video"
                else:
                    cat_display = raw_cat.capitalize()
                
                type_item = QTableWidgetItem(cat_display)
                type_item.setData(Qt.UserRole, raw_cat)
                self.setItem(i, 2, type_item)

                # 3. New Name Preview
                ident_text = vid.get('_new_name') or "-"
                self.setItem(i, 3, QTableWidgetItem(ident_text))

                # 4. Actions
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(8, 8, 8, 8) # Maximum breathing room
                actions_layout.setSpacing(10)

                # 1. FIX button
                fix_btn = QPushButton("🛠️")
                fix_btn.setToolTip("Manual Fix")
                fix_btn.setFixedSize(58, 46)
                fix_btn.setCursor(Qt.PointingHandCursor)
                fix_btn.setStyleSheet(Theme.get_discovery_action_btn_style('primary'))
                fix_btn.clicked.connect(lambda checked=False, v=vid: self.fix_requested.emit(v))
                actions_layout.addWidget(fix_btn)
                
                # 2. FOLDER button
                folder_btn = QPushButton("📂")
                folder_btn.setToolTip("Open Folder")
                folder_btn.setFixedSize(58, 46)
                folder_btn.setCursor(Qt.PointingHandCursor)
                folder_btn.setStyleSheet(Theme.get_discovery_action_btn_style('neutral'))
                folder_btn.clicked.connect(lambda checked=False, p=vid['current_path']: self.open_folder_requested.emit(p))
                actions_layout.addWidget(folder_btn)

                # 3. CLEAR MATCH (Link) button
                clear_btn = QPushButton("🔄")
                clear_btn.setToolTip("Clear Metadata Match")
                clear_btn.setFixedSize(58, 46)
                clear_btn.setCursor(Qt.PointingHandCursor)
                clear_btn.setStyleSheet(Theme.get_discovery_action_btn_style('warning'))
                clear_btn.setEnabled(status == 'MATCHED')
                clear_btn.clicked.connect(lambda checked=False, fid=vid['id']: self.clear_match_requested.emit(fid))
                actions_layout.addWidget(clear_btn)

                # 4. DELETE / RESTORE button
                if status == 'IGNORED':
                    restore_btn = QPushButton("📥")
                    restore_btn.setToolTip("Restore to Library")
                    restore_btn.setFixedSize(58, 46)
                    restore_btn.setCursor(Qt.PointingHandCursor)
                    restore_btn.setStyleSheet(Theme.get_discovery_action_btn_style('success'))
                    restore_btn.clicked.connect(lambda checked=False, fid=vid['id']: self.restore_requested.emit(fid, i))
                    actions_layout.addWidget(restore_btn)
                else:
                    delete_btn = QPushButton("🗑️")
                    delete_btn.setToolTip("Ignore File")
                    delete_btn.setFixedSize(58, 46)
                    delete_btn.setCursor(Qt.PointingHandCursor)
                    delete_btn.setStyleSheet(Theme.get_discovery_action_btn_style('danger'))
                    delete_btn.clicked.connect(lambda checked=False, fid=vid['id']: self.ignore_requested.emit(fid))
                    actions_layout.addWidget(delete_btn)

                self.setCellWidget(i, 4, actions_widget)

            except Exception as row_err:
                import logging
                logging.getLogger(__name__).error(f"Error filling row {i}: {row_err}")

            if i % 10 == 0: QApplication.processEvents()

        self.setSortingEnabled(True)
        self.setUpdatesEnabled(True)

    def apply_filters(self, current_filter, search_text):
        search_text = search_text.lower()
        for row in range(self.rowCount()):
            text_match = not search_text
            if search_text:
                for col in range(4):
                    item = self.item(row, col)
                    if item and (search_text in item.text().lower() or (isinstance(item.data(Qt.UserRole), str) and search_text in item.data(Qt.UserRole).lower())):
                        text_match = True
                        break
            
            btn_match = False
            status_item = self.item(row, 0)
            type_item = self.item(row, 2)
            if status_item and type_item:
                status = status_item.data(Qt.UserRole)
                media_type = type_item.text()
                if current_filter == "ignored": btn_match = (status == 'IGNORED')
                else:
                    raw_cat = type_item.data(Qt.UserRole)
                    if status == 'IGNORED': btn_match = False
                    elif current_filter == "all": btn_match = True
                    elif current_filter == "review": btn_match = (status in ('PENDING', 'MULTIPLE', 'UNCERTAIN', 'NO_MATCH'))
                    elif current_filter == "movies": btn_match = (status == 'MATCHED' and media_type == "Movie")
                    elif current_filter == "shows": btn_match = (status == 'MATCHED' and media_type == "TV Show")
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
                    status = 'LINKED' if file_data.get('parent_file_id') else 'ORPHANED'
                
                status_item = self.item(row, 0)
                if status_item:
                    status_item.setData(Qt.UserRole, status)
                    status_item.setText(status)
                    widget = self.cellWidget(row, 0)
                    if widget:
                        sc = Theme.STATUS_COLORS.get(status, '#64748B')
                        widget.setText(status)
                        widget.setStyleSheet(f"color: {sc}; background: transparent; font-weight: 700; font-size: 11px;")

                # Update Type
                links = engine.db.get_links_for_file(file_id)
                if links:
                    media = engine.db.get_media_item_by_id(links[0]['media_item_id'])
                    if media:
                        mtype = media.get('media_type')
                        raw_cat = file_data.get('category', 'video')
                        if raw_cat == 'video':
                            display = "Movie" if mtype == 'movie' else "TV Show" if mtype == 'tv' else "Video"
                        elif raw_cat == 'extra':
                            display = "Bonus Video"
                        else:
                            display = raw_cat.capitalize()
                        self.setItem(row, 2, QTableWidgetItem(display))

                # Update Preview
                new_name = engine.formatter.generate_name(file_id, engine.config.settings)
                preview = f"{new_name}{os.path.splitext(file_data.get('file_name', ''))[1]}" if new_name else "-"
                self.setItem(row, 3, QTableWidgetItem(preview))
                break
