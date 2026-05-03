from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QWidget,
                             QPushButton, QListWidget, QListWidgetItem, QLabel, QFrame, QScrollArea, QComboBox, QSpinBox)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QPixmap, QIcon
from ui.v3.styles.theme import Theme

class SearchWorker(QThread):
    results_found = Signal(list)

    def __init__(self, engine, query, year, search_type):
        super().__init__()
        self.engine = engine
        self.query = query
        self.year = year
        self.search_type = search_type

    def run(self):
        try:
            results = self.engine.resolver._search_api(self.query, self.year, self.search_type)
            self.results_found.emit(results)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"SearchWorker Error: {e}")
            self.results_found.emit([])

class ManualResolveDialog(QDialog):
    def __init__(self, engine, file_data, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.file_id = file_data['id']
        self.file_name = file_data['file_name']
        self.selected_media = None
        self.search_worker = None

        self.setWindowTitle(f"Manual Resolve: {self.file_name}")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(Theme.get_main_stylesheet())
        
        self._init_ui()
        
        # Pre-fill tools from current data
        self.search_input.setText(file_data.get('fn_title') or file_data.get('fd_title') or self.file_name)
        
        if file_data.get('fn_year'):
            self.year_spin.setValue(int(file_data['fn_year']))
        
        s = file_data.get('fn_season') or file_data.get('fd_season') or 1
        e = file_data.get('fn_episode') or file_data.get('fd_episode') or 1
        try:
            self.season_spin.setValue(int(s))
            self.episode_spin.setValue(int(e))
        except: pass

        self._on_search() # Initial search

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QLabel("Manual Identification")
        header.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        layout.addWidget(header)

        sub_header = QLabel(f"Original file: {self.file_name}")
        sub_header.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 14px;")
        sub_header.setWordWrap(True)
        layout.addWidget(sub_header)
        
        layout.addWidget(Theme.create_hline())

        # Search Tools (Always Visible)
        tools_layout = QVBoxLayout()
        tools_layout.setSpacing(15)

        # Row 1: Title Search
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter title to search...")
        self.search_input.setFixedHeight(45)
        self.search_input.returnPressed.connect(self._on_search)
        
        self.search_btn = QPushButton("Search API")
        self.search_btn.setFixedHeight(45)
        self.search_btn.setFixedWidth(120)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.clicked.connect(self._on_search)
        
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_btn)
        tools_layout.addLayout(search_row)

        # Row 2: Filters & Overrides
        filters_row = QHBoxLayout()
        filters_row.setSpacing(15)
        
        # Type
        type_group = QHBoxLayout()
        type_group.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Movie", "TV Show"])
        self.type_combo.setFixedHeight(35)
        self.type_combo.setFixedWidth(120)
        self.type_combo.currentTextChanged.connect(self._toggle_tv_fields)
        type_group.addWidget(self.type_combo)
        filters_row.addLayout(type_group)
        
        # Year
        year_group = QHBoxLayout()
        year_group.addWidget(QLabel("Year:"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(0, 2100)
        self.year_spin.setValue(0)
        self.year_spin.setSpecialValueText("Any")
        self.year_spin.setFixedHeight(35)
        self.year_spin.setFixedWidth(80)
        year_group.addWidget(self.year_spin)
        filters_row.addLayout(year_group)

        filters_row.addSpacing(20)
        
        # TV Fields Container
        self.tv_fields_container = QWidget()
        tv_fields_layout = QHBoxLayout(self.tv_fields_container)
        tv_fields_layout.setContentsMargins(0, 0, 0, 0)
        tv_fields_layout.setSpacing(15)

        tv_fields_layout.addWidget(QLabel("S:"))
        self.season_spin = QSpinBox()
        self.season_spin.setRange(0, 999)
        self.season_spin.setFixedHeight(35)
        self.season_spin.setFixedWidth(60)
        tv_fields_layout.addWidget(self.season_spin)
        
        tv_fields_layout.addWidget(QLabel("E:"))
        self.episode_spin = QSpinBox()
        self.episode_spin.setRange(0, 999)
        self.episode_spin.setFixedHeight(35)
        self.episode_spin.setFixedWidth(60)
        tv_fields_layout.addWidget(self.episode_spin)
        
        filters_row.addWidget(self.tv_fields_container)
        filters_row.addStretch()
        tools_layout.addLayout(filters_row)
        
        layout.addLayout(tools_layout)

        # Initial visibility
        self._toggle_tv_fields(self.type_combo.currentText())

        # Content (List + Preview)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Results List
        self.results_list = QListWidget()
        self.results_list.setIconSize(QSize(60, 90))
        self.results_list.itemSelectionChanged.connect(self._on_selection_changed)
        content_layout.addWidget(self.results_list, 2)
        
        # Preview Panel
        self.preview_panel = QFrame()
        self.preview_panel.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border: 1px solid {Theme.BORDER}; border-radius: 12px;")
        self.preview_panel.setFixedWidth(280)
        preview_layout = QVBoxLayout(self.preview_panel)
        preview_layout.setContentsMargins(15, 15, 15, 15)
        preview_layout.setSpacing(15)
        
        self.preview_poster = QLabel("No Selection")
        self.preview_poster.setAlignment(Qt.AlignCenter)
        self.preview_poster.setFixedSize(250, 375)
        self.preview_poster.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 8px; border: 1px solid {Theme.BORDER}; color: {Theme.TEXT_DIM};")
        
        self.preview_title = QLabel("Select a result")
        self.preview_title.setWordWrap(True)
        self.preview_title.setStyleSheet(f"font-weight: 800; font-size: 16px; color: {Theme.TEXT_MAIN};")
        
        self.preview_year = QLabel("")
        self.preview_year.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: 700; font-size: 14px;")
        
        preview_layout.addWidget(self.preview_poster, 0, Qt.AlignCenter)
        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_year)
        preview_layout.addStretch()
        
        content_layout.addWidget(self.preview_panel, 1)
        layout.addLayout(content_layout)

        # Footer Buttons
        buttons = QHBoxLayout()
        buttons.setSpacing(15)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setFixedWidth(120)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.confirm_btn = QPushButton("Confirm Match")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setFixedWidth(180)
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.clicked.connect(self._on_confirm)
        
        buttons.addStretch()
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.confirm_btn)
        layout.addLayout(buttons)


    def _toggle_tv_fields(self, current_text):
        """Shows or hides Season/Episode fields based on Media Type."""
        is_tv = (current_text == "TV Show")
        self.tv_fields_container.setVisible(is_tv)

    def _on_search(self):
        query = self.search_input.text().strip()
        if not query: return
        
        # Stop previous search if running
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            self.search_worker.wait()

        self.results_list.clear()
        self.confirm_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        self.search_btn.setText("Searching...")
        
        # Filter by selected type
        selected_text = self.type_combo.currentText()
        search_type = "movie" if selected_text == "Movie" else "tv"
        
        # Use year if provided
        year = self.year_spin.value()
        year_param = str(year) if year > 0 else None

        # Start background search
        self.search_worker = SearchWorker(self.engine, query, year_param, search_type)
        self.search_worker.results_found.connect(self._on_search_results)
        self.search_worker.start()

    def _on_search_results(self, results):
        """Populates the list with API results."""
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search API")
        
        for res in results:
            type_label = "[MOVIE]" if res['media_type'] == 'movie' else "[TV]"
            item = QListWidgetItem(f"{type_label} {res['title']} ({res['year'] or 'N/A'})")
            item.setData(Qt.UserRole, res)
            self.results_list.addItem(item)
        
        if not results:
            self.results_list.addItem("No results found. Try a different title.")

    def _on_selection_changed(self):
        items = self.results_list.selectedItems()
        if not items: return
        
        res = items[0].data(Qt.UserRole)
        self.selected_media = res
        self.confirm_btn.setEnabled(True)
        
        # Sync type combo with selection
        if res['media_type'] == 'tv':
            self.type_combo.setCurrentText("TV Show")
        else:
            self.type_combo.setCurrentText("Movie")

        self.preview_title.setText(res['title'])
        self.preview_year.setText(str(res['year'] or ""))
        
        # Load poster preview
        if res.get('poster_path'):
            self._load_poster(res['poster_path'])
        else:
            self.preview_poster.setText("No Poster")

    def _load_poster(self, poster_path):
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(base_dir, 'data', 'cache', 'posters')
        local_path = os.path.join(cache_dir, poster_path.lstrip('/'))

        # Stop previous worker
        if hasattr(self, 'poster_worker') and self.poster_worker.isRunning():
            try:
                self.poster_worker.finished.disconnect()
                self.poster_worker.terminate()
                self.poster_worker.wait()
            except:
                pass

        # Instant load from cache
        if os.path.exists(local_path):
            pixmap = QPixmap(local_path)
            self._on_poster_loaded(pixmap)
            return

        # Background download
        url = f"https://image.tmdb.org/t/p/w200{poster_path}"
        self.preview_poster.setText("Loading...")
        
        from ui.v3.components.image_loader import ImageDownloader
        self.poster_worker = ImageDownloader(url, local_path)
        self.poster_worker.finished.connect(self._on_poster_loaded)
        self.poster_worker.start()

    def _on_poster_loaded(self, pixmap):
        if not pixmap.isNull():
            scaled = pixmap.scaled(self.preview_poster.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_poster.setPixmap(scaled)
        else:
            self.preview_poster.setText("No Poster")

    def _on_confirm(self):
        if self.selected_media:
            # 1. Update file data with Manual Overrides (Year, Season, Episode)
            self.engine.db.update_file(
                self.file_id, 
                fn_year=self.year_spin.value() if self.year_spin.value() > 0 else None,
                fn_season=self.season_spin.value(),
                fn_episode=str(self.episode_spin.value()),
                fn_media_type=self.selected_media['media_type']
            )

            # 2. Store match in DB
            media_item_id = self.engine.db.upsert_media_item(
                tmdb_id=self.selected_media['tmdb_id'],
                imdb_id=self.selected_media.get('imdb_id'),
                title=self.selected_media['title'],
                year=self.selected_media.get('year'),
                media_type=self.selected_media['media_type'],
                details_json=self.selected_media.get('details_json'),
                poster_path=self.selected_media.get('poster_path')
            )
            self.engine.db.link_file_to_media(self.file_id, media_item_id, 'matched')
            self.accept()
