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
        self.current_type = 'movie' # Default to Movies
        self.nav_stack = [] # Stack of (level, id_or_data) - e.g. ('series', 123), ('season', 1)
        self.current_category = "all"
        self.current_filter_id = None
        
        # Pagination
        self.current_page = 0
        self.page_size = 20
        self.all_data = [] # Store all results for slicing
        
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
        
        back_text = T("common.back")
        if back_text == "common.back": back_text = "Back"
        
        self.btn_back = QPushButton(back_text)
        self.btn_back.setIcon(Theme.get_icon("arrow-left", size=16, color=Theme.TEXT_MAIN))
        self.btn_back.setStyleSheet(Theme.get_secondary_button_style() + "padding: 5px 15px; font-weight: bold;")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self._on_back_clicked)
        self.btn_back.hide()
        
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_back)
        header_layout.addSpacing(10)
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("library.search_placeholder"))
        self.search_input.setFixedWidth(350)
        self.search_input.setStyleSheet(Theme.get_input_style())
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input)
        
        layout.addLayout(header_layout)

        # Tabs Container (Segmented Control)
        self.tabs_container = QFrame()
        self.tabs_container.setObjectName("TabControl")
        self.tabs_container.setFixedHeight(46)
        self.tabs_container.setStyleSheet(f"""
            #TabControl {{
                background-color: {Theme.SURFACE_DARK};
                border-radius: 12px;
                border: 1px solid {Theme.BORDER};
            }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 9px;
                color: {Theme.TEXT_DIM};
                font-weight: bold;
                font-size: 13px;
                padding: 0 25px;
            }}
            QPushButton:checked {{
                background-color: {Theme.PRIMARY};
                color: white;
            }}
            QPushButton:hover:!checked {{
                background-color: rgba(255,255,255,0.05);
            }}
        """)
        
        tabs_inner_layout = QHBoxLayout(self.tabs_container)
        tabs_inner_layout.setContentsMargins(4, 4, 4, 4)
        tabs_inner_layout.setSpacing(4)
        
        self.btn_movies = QPushButton(T("library.tabs.movies") or "Movies")
        self.btn_tv = QPushButton(T("library.tabs.tv") or "TV Shows")
        
        for btn in [self.btn_movies, self.btn_tv]:
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            tabs_inner_layout.addWidget(btn)
        
        self.btn_movies.clicked.connect(lambda: self._on_tab_clicked("movie"))
        self.btn_tv.clicked.connect(lambda: self._on_tab_clicked("tv"))
        
        layout.addWidget(self.tabs_container, 0, Qt.AlignCenter)
        layout.addSpacing(10)

        # Scrollable Gallery Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(Theme.get_scroll_area_style())
        self.scroll.verticalScrollBar().setStyleSheet(Theme.get_scrollbar_style())
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)

        # Placeholder for empty state (perfectly centered in main layout)
        self.empty_placeholder = QWidget()
        self.empty_placeholder.hide()
        placeholder_layout = QVBoxLayout(self.empty_placeholder)
        placeholder_layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_placeholder)

        # 4. Pagination Bar
        self._setup_pagination_ui(layout)

    def _setup_pagination_ui(self, layout):
        self.pagination_container = QWidget()
        self.pagination_layout = QHBoxLayout(self.pagination_container)
        self.pagination_layout.setContentsMargins(0, 10, 0, 0)
        self.pagination_layout.setSpacing(15)
        
        self.prev_btn = QPushButton(T("library.prev_page") if T("library.prev_page") != "library.prev_page" else "Previous")
        self.prev_btn.setFixedWidth(100)
        self.prev_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(self._on_prev_page)
        
        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-weight: bold; font-size: 12px; min-width: 100px;")
        self.page_label.setAlignment(Qt.AlignCenter)
        
        self.next_btn = QPushButton(T("library.next_page") if T("library.next_page") != "library.next_page" else "Next")
        self.next_btn.setFixedWidth(100)
        self.next_btn.setStyleSheet(Theme.get_secondary_button_style())
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(self._on_next_page)
        
        self.pagination_layout.addStretch()
        self.pagination_layout.addWidget(self.prev_btn)
        self.pagination_layout.addWidget(self.page_label)
        self.pagination_layout.addWidget(self.next_btn)
        self.pagination_layout.addStretch()
        
        layout.addWidget(self.pagination_container)
        self.pagination_container.hide()

    def resizeEvent(self, event):
        """Re-render grid on resize to adjust columns."""
        super().resizeEvent(event)
        if hasattr(self, 'all_data') and self.all_data:
            self._render_page()

    def refresh_style(self):
        self.search_input.setStyleSheet(Theme.get_input_style())
        self.scroll.setStyleSheet(Theme.get_scroll_area_style())
        self.scroll.verticalScrollBar().setStyleSheet(Theme.get_scrollbar_style())

    def _on_tab_clicked(self, media_type):
        self.current_type = media_type
        self.nav_stack = [] # Reset navigation when switching tabs
        self.current_page = 0
        self.btn_back.hide()
        self.btn_movies.setChecked(media_type == "movie")
        self.btn_tv.setChecked(media_type == "tv")
        self.refresh_data()



    def _update_tabs_visibility(self):
        """Hides/shows tabs based on actual content in the library."""
        counts = self.engine.db.files.get_library_counts()
        has_movies = counts['movie'] > 0
        has_tv = counts['tv'] > 0
        
        self.btn_movies.setVisible(has_movies)
        self.btn_tv.setVisible(has_tv)
        
        # Hide whole container if empty
        self.tabs_container.setVisible(has_movies or has_tv)
        
        # Adjust default selection if current is hidden
        if self.current_type == 'movie' and not has_movies and has_tv:
            self._on_tab_clicked('tv')
        elif self.current_type == 'tv' and not has_tv and has_movies:
            self._on_tab_clicked('movie')
        elif not has_movies and not has_tv:
            self.current_type = None
            
        self.btn_movies.setChecked(self.current_type == 'movie')
        self.btn_tv.setChecked(self.current_type == 'tv')

    def refresh_data(self):
        """Loads and displays the library gallery based on current navigation level."""
        # 1. Check visibility
        self._update_tabs_visibility()
        
        try:
            search_query = self.search_input.text()
            items = []
            
            # 2. Fetch data based on context
            if self.current_type == 'movie':
                items = self.engine.db.files.get_library_movies(search_query)
            else:
                # TV Show Hierarchy
                if not self.nav_stack:
                    # Root: Show Series
                    items = self.engine.db.files.get_library_series(search_query)
                elif len(self.nav_stack) == 1:
                    # Level 1: Show Seasons for a Series
                    series_id = self.nav_stack[0][1]
                    items = self.engine.db.files.get_library_seasons(series_id)
                else:
                    # Level 2: Show Episodes for a Season
                    series_id = self.nav_stack[0][1]
                    season_num = self.nav_stack[1][1]
                    items = self.engine.db.files.get_library_episodes(series_id, season_num)
            
            self.btn_back.setVisible(len(self.nav_stack) > 0)
            
            self.fill_data(items)

        except Exception as e:
            logger.error(f"Error loading library gallery: {e}")

    def fill_data(self, items):
        """Populates the grid with items for the current page."""
        self.all_data = items
        self._render_page()

    def _render_page(self):
        # 1. Clear current grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.all_data:
            self.pagination_container.hide()
            self.scroll.hide()
            self._show_empty_state()
            return
        
        self.empty_placeholder.hide()
        self.scroll.show()

        # 2. Slice data for current page
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_items = self.all_data[start:end]
        
        # 3. Dynamic Column Calculation & Centering
        card_w = 160
        spacing = 20
        # Use viewport width to account for scrollbar presence
        available_w = self.scroll.viewport().width() - 10 # Buffer to prevent X-scroll
        cols = max(1, (available_w - spacing) // (card_w + spacing))
        
        # Calculate margins to center the entire grid block
        total_grid_w = (cols * card_w) + ((cols - 1) * spacing)
        side_margin = max(0, (available_w - total_grid_w) // 2)
        self.grid_layout.setContentsMargins(side_margin, 0, side_margin, 0)
        self.grid_layout.setSpacing(spacing)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop) # Keep items left-aligned within the centered container
        target_lang = self.engine.config.settings.metadata_language
        
        for i, data in enumerate(page_items):
            row = i // cols
            col = i % cols
            
            poster = PosterWidget(data, target_lang=target_lang)
            poster.clicked.connect(self._on_poster_clicked)
            poster.send_back_requested.connect(self._on_send_back)
            poster.refresh_requested.connect(self._on_refresh_metadata)
            self.grid_layout.addWidget(poster, row, col)

        # 4. Update Pagination UI
        total_pages = max(1, (len(self.all_data) + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"{T('library.page') or 'Page'} {self.current_page + 1} / {total_pages}")
        
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(end < len(self.all_data))
        self.pagination_container.setVisible(len(self.all_data) > self.page_size)

    def _on_prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_page()
            self.scroll.verticalScrollBar().setValue(0)

    def _on_next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.all_data):
            self.current_page += 1
            self._render_page()
            self.scroll.verticalScrollBar().setValue(0)

    def _show_empty_state(self):
        # Clear previous placeholder content
        while self.empty_placeholder.layout().count():
            item = self.empty_placeholder.layout().takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        self.empty_placeholder.show()
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(Theme.get_pixmap("film", size=100, color=Theme.TEXT_DIM))
        icon_lbl.setAlignment(Qt.AlignCenter)
        
        title = QLabel(T("library.empty_title") or "Your Library is empty")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        
        desc = QLabel(T("library.empty_desc") or "Start organizing your files to see them here in all their glory.")
        desc.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-size: 16px;")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setFixedWidth(500)
        
        self.empty_placeholder.layout().addStretch()
        self.empty_placeholder.layout().addWidget(icon_lbl)
        self.empty_placeholder.layout().addWidget(title)
        self.empty_placeholder.layout().addWidget(desc)
        self.empty_placeholder.layout().addStretch()

    def _on_search_changed(self, text):
        self.current_page = 0
        self.refresh_data()

    def _on_poster_clicked(self, data):
        """Handle drill-down navigation or opening file."""
        if self.current_type == 'movie':
            self._open_file_folder(data)
            return
            
        # TV Logic
        if not self.nav_stack:
            # Clicked a Series -> Go to Seasons
            self.nav_stack.append(('series', data['id']))
            self.current_page = 0
            self.refresh_data()
        elif len(self.nav_stack) == 1:
            # Clicked a Season -> Go to Episodes
            self.nav_stack.append(('season', data['season_number']))
            self.current_page = 0
            self.refresh_data()
        else:
            # Clicked an Episode -> Open folder
            self._open_file_folder(data)

    def _on_back_clicked(self):
        if self.nav_stack:
            self.nav_stack.pop()
            self.current_page = 0
            self.refresh_data()

    def _open_file_folder(self, data):
        """Opens the OS file explorer for the selected item."""
        path = data.get('current_path')
        if path and os.path.exists(path):
            import subprocess
            if os.name == 'nt':
                os.startfile(os.path.dirname(path))
            else:
                subprocess.run(['open', os.path.dirname(path)])
        else:
            # If it's a series/season card, it won't have a current_path here
            pass

    def _on_send_back(self, file_id):
        """Moves a file from the Library back to the Discovery workspace."""
        try:
            self.engine.db.files.update_file(file_id, status='matched')
            self.refresh_data()
        except Exception as e:
            logger.error(f"Error sending file back to workspace: {e}")
            QMessageBox.critical(self, T("common.error"), str(e))

    def _on_refresh_metadata(self, data):
        """Force re-fetches metadata for an item."""
        tmdb_id = data.get('tmdb_id')
        if not tmdb_id: return
        
        # Determine what to refresh
        try:
            if 'episode_number' in data:
                # Refresh entire season to get all stills
                self.engine.library_manager.fetch_and_store_season(
                    tmdb_id, data['season_number'], force_refresh=True
                )
            elif 'season_number' in data:
                self.engine.library_manager.fetch_and_store_season(
                    tmdb_id, data['season_number'], force_refresh=True
                )
            else:
                # Movie or Series
                media_type = data.get('media_item_type') or data.get('media_type')
                self.engine.library_manager.store_result(
                    {'tmdb_id': tmdb_id, 'media_type': media_type}, 
                    force_refresh=True
                )
            
            # Update UI
            self.refresh_data()
            QApplication.processEvents() # Ensure UI updates
        except Exception as e:
            logger.error(f"Manual refresh failed: {e}")
