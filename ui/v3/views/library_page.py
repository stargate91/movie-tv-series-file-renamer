import os
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QScrollArea, QFrame, QGridLayout,
                             QApplication, QMessageBox, QPushButton)
from PySide6.QtCore import Qt, Signal, QSize
from ui.v3.styles.theme import Theme
from ui.v3.components.poster_widget import PosterWidget
from core.i18n import T

logger = logging.getLogger(__name__)

class LibraryPage(QWidget):
    """Gallery view for browsing the organized media collection."""
    
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
        title = QLabel(T("library.title"))
        title.setStyleSheet(Theme.get_page_header_style())
        subtitle = QLabel(T("library.subtitle"))
        subtitle.setStyleSheet(Theme.get_card_description_style())
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("library.search_placeholder"))
        self.search_input.setFixedWidth(350)
        self.search_input.setStyleSheet(Theme.get_input_style())
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input)
        
        layout.addLayout(header_layout)

        # Scrollable Gallery Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(Theme.get_scroll_area_style())
        self.scroll.verticalScrollBar().setStyleSheet(Theme.get_scrollbar_style())
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)

    def refresh_style(self):
        self.search_input.setStyleSheet(Theme.get_input_style())
        self.scroll.setStyleSheet(Theme.get_scroll_area_style())
        self.scroll.verticalScrollBar().setStyleSheet(Theme.get_scrollbar_style())

    def refresh_data(self):
        """Loads and displays the library gallery."""
        # 1. Clear current grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        try:
            # 2. Fetch library files
            search_query = self.search_input.text()
            files = self.engine.db.files.get_library_files(search_query)
            
            if not files:
                self.grid_layout.setAlignment(Qt.AlignCenter)
                self._show_empty_state()
                return

            self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            # 3. Populate grid
            cols = 5 # Default columns
            for i, file_data in enumerate(files):
                row = i // cols
                col = i % cols
                
                poster = PosterWidget(file_data)
                poster.clicked.connect(self._on_poster_clicked)
                poster.send_back_requested.connect(self._on_send_back)
                self.grid_layout.addWidget(poster, row, col)

        except Exception as e:
            logger.error(f"Error loading library gallery: {e}")

    def _show_empty_state(self):
        empty_widget = QWidget()
        empty_widget.setMinimumHeight(400) # Ensure it has some height for centering
        vbox = QVBoxLayout(empty_widget)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setSpacing(10)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(Theme.get_pixmap("film", size=80, color=Theme.TEXT_DIM))
        icon_lbl.setAlignment(Qt.AlignCenter)
        
        title = QLabel(T("library.empty_title"))
        title.setStyleSheet(Theme.get_preview_title_style())
        title.setAlignment(Qt.AlignCenter)
        
        desc = QLabel(T("library.empty_desc"))
        desc.setStyleSheet(Theme.get_card_description_style())
        desc.setAlignment(Qt.AlignCenter)
        
        vbox.addStretch()
        vbox.addWidget(icon_lbl)
        vbox.addWidget(title)
        vbox.addWidget(desc)
        vbox.addStretch()
        
        self.grid_layout.addWidget(empty_widget, 0, 0)

    def _on_search_changed(self, text):
        # Debounce or just refresh
        self.refresh_data()

    def _on_poster_clicked(self, data):
        """Show details for the selected media item."""
        # For now, just open the folder as a basic action
        path = data.get('current_path')
        if path and os.path.exists(path):
            import subprocess
            if os.name == 'nt':
                os.startfile(os.path.dirname(path))
            else:
                subprocess.run(['open', os.path.dirname(path)])
        else:
            QMessageBox.warning(self, T("common.error"), f"File not found: {path}")

    def _on_send_back(self, file_id):
        """Moves a file from the Library back to the Discovery workspace."""
        try:
            self.engine.db.files.update_file(file_id, status='matched')
            self.refresh_data()
        except Exception as e:
            logger.error(f"Error sending file back to workspace: {e}")
            QMessageBox.critical(self, T("common.error"), str(e))
