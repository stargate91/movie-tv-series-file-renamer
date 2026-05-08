import os
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QScrollArea, QFrame, 
                             QApplication, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, Signal
from ui.v3.styles.theme import Theme
from ui.v3.workers.discovery_workers import UndoWorker
from core.i18n import T

logger = logging.getLogger(__name__)

class HistoryBatchCard(QFrame):
    """A collapsible card representing a single rename operation batch."""
    undo_requested = Signal(str) # batch_id

    def __init__(self, batch_data, parent=None):
        super().__init__(parent)
        self.batch_id = batch_data[0]['batch_id']
        self.items = batch_data
        self.is_expanded = False
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("BatchCard")
        self.setStyleSheet(Theme.get_history_batch_card_style())
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # Header Row
        header_layout = QHBoxLayout()
        
        # Icon & Info
        info_layout = QVBoxLayout()
        ts = self.items[0].get('timestamp', T("history.unknown_date"))
        date_lbl = QLabel(ts)
        date_lbl.setStyleSheet(Theme.get_status_label_style())
        
        title_lbl = QLabel(T("history.renamed_count", count=len(self.items)))
        title_lbl.setStyleSheet(Theme.get_preview_title_style())
        
        info_layout.addWidget(date_lbl)
        info_layout.addWidget(title_lbl)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()

        # Undo Button
        self.undo_btn = QPushButton(T('history.undo_btn'))
        self.undo_btn.setIcon(Theme.get_icon("refresh", size=16, color=Theme.TEXT_MAIN))
        self.undo_btn.setCursor(Qt.PointingHandCursor)
        self.undo_btn.setStyleSheet(Theme.get_history_undo_button_style())
        self.undo_btn.clicked.connect(lambda: self.undo_requested.emit(self.batch_id))
        
        # Expand Button
        self.expand_btn = QPushButton(T("history.expand"))
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setStyleSheet(Theme.get_history_expand_button_style())
        self.expand_btn.clicked.connect(self.toggle_expand)

        header_layout.addWidget(self.undo_btn)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.expand_btn)
        
        self.main_layout.addLayout(header_layout)

        # Details Container (hidden by default)
        self.details_container = QWidget()
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setContentsMargins(0, 10, 0, 0)
        self.details_layout.setSpacing(5)
        
        for item in self.items:
            row = QFrame()
            row.setStyleSheet(Theme.get_batch_card_style())
            row_layout = QHBoxLayout(row)
            
            old_name = os.path.basename(item['old_path'] or "")
            new_name = os.path.basename(item['new_path'] or "")
            
            lbl = QLabel(f"{old_name}  →  {new_name}")
            lbl.setStyleSheet(Theme.get_monospace_label_style())
            row_layout.addWidget(lbl)
            self.details_layout.addWidget(row)
            
        self.details_container.hide()
        self.main_layout.addWidget(self.details_container)

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.details_container.setVisible(self.is_expanded)
        self.expand_btn.setText(T("history.collapse") if self.is_expanded else T("history.expand"))

class HistoryPage(QWidget):
    """View for browsing and undoing previous rename operations."""
    
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.active_workers = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header Section
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title = QLabel(T("history.title"))
        title.setStyleSheet(Theme.get_page_header_style())
        subtitle = QLabel(T("history.subtitle"))
        subtitle.setStyleSheet(Theme.get_card_description_style())
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("history.search_placeholder"))
        self.search_input.setFixedWidth(350)
        self.search_input.setStyleSheet(Theme.get_input_style())
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input)
        
        layout.addLayout(header_layout)

        # Scrollable Content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(Theme.get_scroll_area_style())
        self.scroll.verticalScrollBar().setStyleSheet(Theme.get_scrollbar_style())
        
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(15)
        self.content_layout.addStretch()
        
        self.scroll.setWidget(self.content_container)
        layout.addWidget(self.scroll)

        # Status Area (Progress Bar)
        self._setup_status_area(layout)

    def _setup_status_area(self, layout):
        self.progress_container = QWidget()
        self.progress_container.hide()
        p_layout = QVBoxLayout(self.progress_container)
        p_layout.setContentsMargins(0, 10, 0, 0)
        p_layout.setSpacing(8)
        
        # Horizontal layout for Status + Abort
        h_layout = QHBoxLayout()
        self.status_info = QLabel("")
        self.status_info.setStyleSheet(Theme.get_status_label_style())
        
        self.abort_btn = QPushButton(T("discovery.abort"))
        self.abort_btn.setFixedWidth(100)
        self.abort_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.abort_btn.setCursor(Qt.PointingHandCursor)
        self.abort_btn.clicked.connect(self._on_abort_requested)
        
        h_layout.addWidget(self.status_info)
        h_layout.addStretch()
        h_layout.addWidget(self.abort_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setStyleSheet(Theme.get_progress_bar_detailed_style())
        
        p_layout.addLayout(h_layout)
        p_layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_container)

    def _set_ui_locked(self, locked):
        """Disables/Enables interactive elements during long operations."""
        self.search_input.setEnabled(not locked)
        # Disable all undo buttons on cards
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if isinstance(widget, HistoryBatchCard):
                widget.undo_btn.setEnabled(not locked)

    def refresh_style(self):
        """Refreshes dynamic styles for the page."""
        self.search_input.setStyleSheet(Theme.get_input_style())
        self.scroll.setStyleSheet(Theme.get_scroll_area_style())
        self.scroll.verticalScrollBar().setStyleSheet(Theme.get_scrollbar_style())
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setStyleSheet(Theme.get_progress_bar_detailed_style())
        if hasattr(self, 'status_info'):
            self.status_info.setStyleSheet(Theme.get_status_label_style())

    def refresh_data(self):
        """Loads and groups history entries from the database."""
        # Clear current list
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        try:
            # 1. Fetch all history entries
            raw_history = self.engine.db.history.get_recent(limit=500)
            if not raw_history:
                empty_lbl = QLabel(T("history.no_history"))
                empty_lbl.setStyleSheet(Theme.get_settings_title_style())
                empty_lbl.setAlignment(Qt.AlignCenter)
                self.content_layout.insertWidget(0, empty_lbl)
                return

            # 2. Group by batch_id
            batches = {}
            for row in raw_history:
                bid = row['batch_id']
                if bid not in batches: batches[bid] = []
                batches[bid].append(dict(row))

            # 3. Create cards (in reverse chronological order)
            # dict keys order is not guaranteed to be chronological by bid, 
            # but raw_history is sorted by timestamp DESC.
            processed_bids = []
            for row in raw_history:
                bid = row['batch_id']
                if bid in processed_bids: continue
                processed_bids.append(bid)
                
                card = HistoryBatchCard(batches[bid])
                card.undo_requested.connect(self._on_undo_requested)
                self.content_layout.insertWidget(self.content_layout.count()-1, card)

        except Exception as e:
            logger.error(f"Error loading history: {e}")

    def _on_search_changed(self, text):
        # Filter visible cards
        query = text.lower()
        for i in range(self.content_layout.count()):
            item = self.content_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, HistoryBatchCard):
                # Search in all items within the batch
                match = any(query in os.path.basename(f['old_path']).lower() or 
                           query in os.path.basename(f['new_path']).lower() for f in widget.items)
                widget.setVisible(match)

    def _on_undo_requested(self, batch_id):
        if QMessageBox.question(self, T("history.undo_btn"), T("discovery.messages.undo_confirm")) == QMessageBox.Yes:
            self._set_ui_locked(True)
            self.progress_container.show()
            self.progress_bar.setValue(0)
            self.status_info.setText(T("discovery.messages.restoring") if T("discovery.messages.restoring") != "discovery.messages.restoring" else "Restoring items...")
            
            worker = UndoWorker(self.engine, batch_id)
            self.active_workers.append(worker)
            worker.progress.connect(self._on_worker_progress)
            worker.finished.connect(self._on_undo_finished)
            worker.finished.connect(lambda: self.active_workers.remove(worker) if worker in self.active_workers else None)
            worker.start()

    def _on_abort_requested(self):
        for worker in self.active_workers:
            if isinstance(worker, UndoWorker):
                worker.stop()
        self.status_info.setText(T("discovery.messages.aborting"))
        self.abort_btn.setEnabled(False)

    def _on_worker_progress(self, val, text):
        self.progress_bar.setValue(val)
        self.status_info.setText(text)

    def _on_undo_finished(self, results):
        self.progress_container.hide()
        self._set_ui_locked(False)
        self.abort_btn.setEnabled(True)
        
        success = results.get('success', 0)
        failed = results.get('failed', 0)
        
        if success > 0 and failed == 0:
            QMessageBox.information(self, T("history.undo_success_title"), T("discovery.messages.undo_success", count=success))
            self.refresh_data()
        elif failed > 0:
            QMessageBox.warning(self, T("history.undo_partial_title"), T("discovery.messages.undo_errors_msg", count=failed))
            self.refresh_data()
        else:
            # Handle case where results are empty or success=0
            errors = results.get('errors', [])
            if errors:
                QMessageBox.warning(self, T("history.undo_partial_title"), errors[0])
            self.refresh_data()
