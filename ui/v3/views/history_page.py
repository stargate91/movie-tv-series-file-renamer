import os
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QScrollArea, QFrame, 
                             QApplication, QMessageBox)
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
        self.setStyleSheet(f"""
            #BatchCard {{
                background: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER};
                border-radius: 12px;
            }}
            #BatchCard:hover {{
                border-color: {Theme.PRIMARY}88;
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # Header Row
        header_layout = QHBoxLayout()
        
        # Icon & Info
        info_layout = QVBoxLayout()
        ts = self.items[0].get('timestamp', 'Unknown date')
        date_lbl = QLabel(ts)
        date_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; font-weight: 600;")
        
        title_lbl = QLabel(T("history.renamed_count", count=len(self.items)))
        title_lbl.setStyleSheet("color: white; font-size: 15px; font-weight: 800;")
        
        info_layout.addWidget(date_lbl)
        info_layout.addWidget(title_lbl)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()

        # Undo Button
        self.undo_btn = QPushButton(f"🔄 {T('history.undo_btn')}")
        self.undo_btn.setCursor(Qt.PointingHandCursor)
        self.undo_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.PRIMARY}15;
                color: {Theme.PRIMARY};
                border: 1px solid {Theme.PRIMARY}44;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {Theme.PRIMARY};
                color: white;
            }}
        """)
        self.undo_btn.clicked.connect(lambda: self.undo_requested.emit(self.batch_id))
        
        # Expand Button
        self.expand_btn = QPushButton(T("history.expand"))
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setStyleSheet(f"color: {Theme.TEXT_DIM}; background: transparent; border: none; font-weight: 700;")
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
            row.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border-radius: 6px;")
            row_layout = QHBoxLayout(row)
            
            old_name = os.path.basename(item['old_path'] or "")
            new_name = os.path.basename(item['new_path'] or "")
            
            lbl = QLabel(f"{old_name}  →  {new_name}")
            lbl.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-family: monospace; font-size: 12px;")
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
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header Section
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title = QLabel(T("history.title"))
        title.setStyleSheet("font-size: 28px; font-weight: 800; color: white;")
        subtitle = QLabel(T("history.subtitle"))
        subtitle.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px;")
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("history.search_placeholder"))
        self.search_input.setFixedWidth(350)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {Theme.SURFACE_DARK};
                border: 1px solid {Theme.BORDER};
                border-radius: 8px;
                padding: 10px 15px;
                color: white;
            }}
            QLineEdit:focus {{ border-color: {Theme.PRIMARY}; }}
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input)
        
        layout.addLayout(header_layout)

        # Scrollable Content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        self.scroll.verticalScrollBar().setStyleSheet(Theme.get_scrollbar_style())
        
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(15)
        self.content_layout.addStretch()
        
        self.scroll.setWidget(self.content_container)
        layout.addWidget(self.scroll)

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
                empty_lbl.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-size: 16px;")
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
            self.undo_worker = UndoWorker(self.engine, batch_id)
            self.undo_worker.finished.connect(self._on_undo_finished)
            self.undo_worker.start()

    def _on_undo_finished(self, results):
        if results.get('success', 0) > 0:
            QMessageBox.information(self, "Success", f"Reverted {results['success']} files.")
            self.refresh_data()
        if results.get('failed', 0) > 0:
            QMessageBox.warning(self, "Partial Success", f"Failed to revert {results['failed']} files.")
            self.refresh_data()
