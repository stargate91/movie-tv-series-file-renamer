from PySide6.QtCore import Qt, QSize, QThread, Signal, Slot, QEvent
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QWidget,
                             QPushButton, QListWidget, QListWidgetItem, QLabel, QFrame, QScrollArea, QComboBox, QSpinBox)
import re
from PySide6.QtGui import QPixmap, QIcon
from ui.v3.styles.theme import Theme

class SearchWorker(QThread):
    results_found = Signal(list, str) # results, mode

    def __init__(self, engine, query, year, search_type, mode="search", parent_id=None, season_num=None):
        super().__init__()
        self.engine = engine
        self.query = query
        self.year = year
        self.search_type = search_type
        self.mode = mode
        self.parent_id = parent_id # tmdb_id of show
        self.season_num = season_num

    def run(self):
        import logging
        log = logging.getLogger(__name__)
        lang = self.engine.resolver.language
        # Force print to stdout for debugging
        print(f"[ManualResolve] Worker START: mode={self.mode}, query='{self.query}', year={self.year}, lang={lang}")
        try:
            if self.mode == "search":
                s_match = re.search(r'[sS](\d+)', self.query)
                e_match = re.search(r'[eE](\d+)', self.query)
                clean_query = re.sub(r'[sS]\d+|[eE]\d+', '', self.query).strip()
                
                print(f"[ManualResolve] Executing API Search for '{clean_query}' (Year: {self.year}, Lang: {lang})...")
                results = self.engine.resolver._search_api(clean_query, self.year, self.search_type)
                print(f"[ManualResolve] API Search returned {len(results)} items.")
                
                if self.search_type == "tv" and results and (s_match or e_match):
                    best_show = results[0]
                    s_num = int(s_match.group(1)) if s_match else None
                    e_num = int(e_match.group(1)) if e_match else None
                    
                    if s_num is not None:
                        print(f"[ManualResolve] Drilling to S{s_num} for show {best_show['tmdb_id']}")
                        eps = self.engine.resolver.api.get_from_tmdb_season(best_show['tmdb_id'], s_num, language=lang)
                        ep_results = []
                        for ep in eps.get('episodes', []):
                            ep_results.append({
                                'tmdb_id': ep['id'],
                                'title': f"S{str(s_num).zfill(2)}E{str(ep['episode_number']).zfill(2)} - {ep['name']}",
                                'media_type': 'episode',
                                'show_id': best_show['tmdb_id'],
                                'season_number': s_num,
                                'episode_number': ep['episode_number'],
                                'poster_path': ep.get('still_path') or best_show.get('poster_path')
                            })
                        print(f"[ManualResolve] Emitting {len(ep_results)} episodes.")
                        self.results_found.emit(ep_results, "episodes")
                        return

                self.results_found.emit(results, "search")

            elif self.mode == "seasons":
                print(f"[ManualResolve] Fetching seasons for {self.parent_id} (Lang: {lang})")
                data = self.engine.resolver.api.get_from_tmdb_tv_detail(self.parent_id, language=lang)
                results = []
                for s in data.get('seasons', []):
                    results.append({
                        'tmdb_id': s['id'], 'title': s['name'], 'media_type': 'season',
                        'show_id': self.parent_id, 'season_number': s['season_number'],
                        'episode_count': s.get('episode_count'), 'poster_path': s.get('poster_path')
                    })
                self.results_found.emit(results, "seasons")

            elif self.mode == "episodes":
                print(f"[ManualResolve] Fetching episodes for {self.parent_id} S{self.season_num} (Lang: {lang})")
                data = self.engine.resolver.api.get_from_tmdb_season(self.parent_id, self.season_num, language=lang)
                results = []
                for ep in data.get('episodes', []):
                    results.append({
                        'tmdb_id': ep['id'], 'title': f"E{str(ep['episode_number']).zfill(2)} - {ep['name']}",
                        'media_type': 'episode', 'show_id': self.parent_id,
                        'season_number': self.season_num, 'episode_number': ep['episode_number'],
                        'poster_path': ep.get('still_path'), 'overview': ep.get('overview')
                    })
                self.results_found.emit(results, "episodes")

        except Exception as e:
            print(f"[ManualResolve] Worker CRASH: {e}")
            log.error(f"SearchWorker Error: {e}", exc_info=True)
            self.results_found.emit([], "error")
        print("[ManualResolve] Worker FINISHED.")

class ManualResolveDialog(QDialog):
    def __init__(self, engine, file_data, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.file_id = file_data['id']
        self.file_name = file_data['file_name']
        self.selected_media = None # Currently highlighted result
        self.basket = [] # List of confirmed selections
        self.search_worker = None
        self.nav_stack = [] # History of (mode, parent_id, season_num, title)
        self.multi_match_mode = False # Default to simple mode

        self.setWindowTitle(f"Manual Resolve: {self.file_name}")
        self.setMinimumSize(850, 750) # Narrower default
        self.setStyleSheet(Theme.get_main_stylesheet())
        
        self._init_ui()
        
        # 1. Pre-fill title
        self.search_input.setText(file_data.get('fn_title') or file_data.get('fd_title') or "")
        
        # 2. Pre-fill Year
        if file_data.get('fn_year'):
            try: self.year_spin.setValue(int(file_data['fn_year']))
            except: pass
        
        # 3. Detect Media Type and Pre-fill S/E
        m_type = file_data.get('fn_media_type') or file_data.get('fd_media_type') or 'movie'
        s_val = file_data.get('fn_season') or file_data.get('fd_season') or 0
        e_val = file_data.get('fn_episode') or file_data.get('fd_episode') or 0
        
        # If we have season/episode info, it's definitely a TV Show
        if s_val or e_val or m_type == 'tv':
            self.type_combo.setCurrentText("TV Show")
            try:
                self.season_spin.setValue(int(s_val))
                self.episode_spin.setValue(int(e_val))
            except: pass
        else:
            self.type_combo.setCurrentText("Movie")

        # 4. Check for existing candidates (if file was MULTIPLE)
        candidates = self.engine.db.get_candidates(self.file_id)
        if candidates:
            self.nav_label.setText(f"Found {len(candidates)} Possible Matches")
            self.results_list.clear()
            for cand in candidates:
                icon = "📺" if cand['media_type'] == 'tv' else "🎬"
                label = f"{icon} {cand['title']}"
                if cand.get('year'): label += f" ({cand['year']})"
                
                item = QListWidgetItem(label)
                res_dict = {
                    'tmdb_id': cand['tmdb_id'],
                    'title': cand['title'],
                    'year': cand['year'],
                    'media_type': cand['media_type'],
                    'poster_path': cand['poster_path']
                }
                item.setData(Qt.UserRole, res_dict)
                self.results_list.addItem(item)
        else:
            # Initial search only if we have a title
            if self.search_input.text():
                self._on_search()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setSpacing(15)

        # Top Bar: Navigation + Mode Toggle
        top_bar = QHBoxLayout()
        
        # Left: Back button + Title
        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("SecondaryButton")
        self.back_btn.setFixedWidth(80)
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._on_back)
        
        self.nav_label = QLabel("Search Results")
        self.nav_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Theme.TEXT_MAIN};")
        
        top_bar.addWidget(self.back_btn)
        top_bar.addWidget(self.nav_label)
        top_bar.addStretch()

        # Right: Multi-Match Toggle
        self.mode_btn = QPushButton("Link Multiple Items")
        self.mode_btn.setObjectName("SecondaryButton")
        self.mode_btn.setFixedWidth(160)
        self.mode_btn.setCheckable(True)
        self.mode_btn.clicked.connect(self._toggle_multi_match)
        top_bar.addWidget(self.mode_btn)
        
        layout.addLayout(top_bar)
        layout.addWidget(Theme.create_hline())

        # Search Tools
        tools_layout = QVBoxLayout()
        tools_layout.setSpacing(10)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title... (e.g. 'Stargate S01')")
        self.search_input.setFixedHeight(40)
        self.search_input.returnPressed.connect(lambda: self._on_search())
        
        self.search_btn = QPushButton("Search API")
        self.search_btn.setFixedHeight(40)
        self.search_btn.setFixedWidth(100)
        self.search_btn.clicked.connect(lambda: self._on_search())
        
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_btn)
        tools_layout.addLayout(search_row)

        filters_row = QHBoxLayout()
        filters_row.setSpacing(15)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Movie", "TV Show"])
        self.type_combo.setFixedWidth(110)
        self.type_combo.currentTextChanged.connect(self._toggle_tv_fields)
        filters_row.addWidget(QLabel("Type:"))
        filters_row.addWidget(self.type_combo)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(0, 2100)
        self.year_spin.setSpecialValueText("Any Year")
        self.year_spin.setFixedWidth(90)
        self._setup_auto_clear_spin(self.year_spin)
        filters_row.addWidget(QLabel("Year:"))
        filters_row.addWidget(self.year_spin)

        self.tv_fields_container = QWidget()
        tv_fields_layout = QHBoxLayout(self.tv_fields_container)
        tv_fields_layout.setContentsMargins(0, 0, 0, 0)
        tv_fields_layout.addWidget(QLabel("S:"))
        self.season_spin = QSpinBox()
        self.season_spin.setRange(0, 999)
        self.season_spin.setSpecialValueText("None")
        self._setup_auto_clear_spin(self.season_spin)
        tv_fields_layout.addWidget(self.season_spin)
        tv_fields_layout.addWidget(QLabel("E:"))
        self.episode_spin = QSpinBox()
        self.episode_spin.setRange(0, 999)
        self.episode_spin.setSpecialValueText("None")
        self._setup_auto_clear_spin(self.episode_spin)
        tv_fields_layout.addWidget(self.episode_spin)
        
        filters_row.addWidget(self.tv_fields_container)
        filters_row.addStretch()
        tools_layout.addLayout(filters_row)
        layout.addLayout(tools_layout)

        # Main Content Layout (Horizontal)
        self.content_row = QHBoxLayout()
        self.content_row.setSpacing(20)
        
        # Col 1: Results
        res_col = QVBoxLayout()
        self.results_list = QListWidget()
        self.results_list.setIconSize(QSize(60, 90))
        self.results_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        res_col.addWidget(self.results_list)
        
        self.action_btn = QPushButton("Match This Item")
        self.action_btn.setFixedHeight(45)
        self.action_btn.setEnabled(False)
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.PRIMARY};
                color: white;
                font-weight: 800;
                font-size: 15px;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: #3b82f6;
            }}
            QPushButton:disabled {{
                background: #1e293b;
                color: #64748b;
            }}
        """)
        self.action_btn.clicked.connect(self._on_action_clicked)
        res_col.addWidget(self.action_btn)
        self.content_row.addLayout(res_col, 2)
        
        # Col 2: Preview
        self.preview_panel = QFrame()
        self.preview_panel.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border: 1px solid {Theme.BORDER}; border-radius: 12px;")
        self.preview_panel.setFixedWidth(280)
        preview_layout = QVBoxLayout(self.preview_panel)
        
        self.preview_poster = QLabel("No Selection")
        self.preview_poster.setAlignment(Qt.AlignCenter)
        self.preview_poster.setFixedSize(250, 375)
        self.preview_poster.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 8px;")
        
        self.preview_title = QLabel("Select a result")
        self.preview_title.setWordWrap(True)
        self.preview_title.setStyleSheet(f"font-weight: 800; font-size: 16px; color: {Theme.TEXT_MAIN};")
        
        self.preview_meta = QLabel("")
        self.preview_meta.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: 700;")
        
        self.preview_overview = QLabel("")
        self.preview_overview.setWordWrap(True)
        self.preview_overview.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 12px;")
        
        preview_layout.addWidget(self.preview_poster, 0, Qt.AlignCenter)
        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_meta)
        preview_layout.addWidget(self.preview_overview)
        preview_layout.addStretch()
        self.content_row.addWidget(self.preview_panel)
        
        # Col 3: Basket (Hidden by default)
        self.basket_widget = QWidget()
        self.basket_widget.setVisible(False)
        basket_layout = QVBoxLayout(self.basket_widget)
        basket_layout.setContentsMargins(0, 0, 0, 0)
        
        basket_header = QHBoxLayout()
        basket_header.addWidget(QLabel("Basket"))
        self.clear_basket_btn = QPushButton("Clear")
        self.clear_basket_btn.setObjectName("SecondaryButton")
        self.clear_basket_btn.clicked.connect(self._clear_basket)
        basket_header.addWidget(self.clear_basket_btn)
        basket_layout.addLayout(basket_header)
        
        self.basket_list = QListWidget()
        self.basket_list.setStyleSheet(f"background: {Theme.SURFACE_LIGHT};")
        basket_layout.addWidget(self.basket_list)
        
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self._remove_from_basket)
        basket_layout.addWidget(self.remove_btn)
        
        self.confirm_btn = QPushButton("Confirm & Link All")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setFixedHeight(45)
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.SUCCESS};
                color: white;
                font-weight: 800;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: #22c55e;
            }}
            QPushButton:disabled {{
                background: #064e3b;
                color: #34d399;
                opacity: 0.5;
            }}
        """)
        self.confirm_btn.clicked.connect(self._on_confirm)
        basket_layout.addWidget(self.confirm_btn)
        
        self.content_row.addWidget(self.basket_widget, 2)
        layout.addLayout(self.content_row)

        # Footer (Cancel only in simple mode)
        footer = QHBoxLayout()
        self.footer_cancel = QPushButton("Cancel", clicked=self.reject, objectName="SecondaryButton", fixedWidth=120, fixedHeight=40)
        footer.addStretch()
        footer.addWidget(self.footer_cancel)
        layout.addLayout(footer)

        self._toggle_tv_fields(self.type_combo.currentText())

    def _toggle_multi_match(self, checked):
        self.multi_match_mode = checked
        self.basket_widget.setVisible(checked)
        
        if checked:
            self.setMinimumSize(1150, 750)
            self.resize(1150, 750)
            self.action_btn.setText("+ Add Selection to Basket")
            self.mode_btn.setText("Back to Simple Mode")
        else:
            self.setMinimumSize(850, 750)
            self.resize(850, 750)
            self.action_btn.setText("Match This Item")
            self.mode_btn.setText("Link Multiple Items")

    def _on_action_clicked(self):
        if not self.selected_media: return
        
        if self.multi_match_mode:
            self._add_to_basket()
        else:
            # Simple Mode: Single Item Match
            # Wrap in a temporary basket and confirm
            m = self.selected_media
            s = m.get('season_number', self.season_spin.value())
            e = m.get('episode_number', self.episode_spin.value())
            self.basket = [{'media': m, 's': s, 'e': e}]
            self._on_confirm()

    def _setup_auto_clear_spin(self, spin):
        """Install event filter on the internal line edit to catch 'empty' state."""
        spin.lineEdit().installEventFilter(self)

    def eventFilter(self, source, event):
        if event.type() == QEvent.FocusOut:
            # Check if source is one of our spinbox line edits
            for s in [self.year_spin, self.season_spin, self.episode_spin]:
                if source is s.lineEdit():
                    if not source.text().strip():
                        s.setValue(0)
                        return True
        return super().eventFilter(source, event)

    def _toggle_tv_fields(self, current_text):
        """Shows or hides Season/Episode fields based on Media Type."""
        is_tv = (current_text == "TV Show")
        if hasattr(self, 'tv_fields_container'):
            self.tv_fields_container.setVisible(is_tv)

    def _on_search(self, mode="search", parent_id=None, season_num=None, title=None):
        query = self.search_input.text().strip()
        if not query and mode == "search": return
        
        # Safe cleanup of old worker
        if self.search_worker and self.search_worker.isRunning():
            try: self.search_worker.results_found.disconnect()
            except: pass

        self.results_list.clear()
        self.results_list.addItem("Searching API...")
        self.action_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        self.search_btn.setText("Wait...")
        
        if mode == "search":
            self.nav_stack = []
            self.back_btn.setVisible(False)
            self.nav_label.setText("Search Results")
        else:
            self.back_btn.setVisible(True)
            self.nav_label.setText(title or "Browsing...")

        search_type = "movie" if self.type_combo.currentText() == "Movie" else "tv"
        year = self.year_spin.value()
        year_param = str(year) if year > 0 else None
        print(f"[ManualResolve] UI Search Trigger: query='{query}', year_param='{year_param}'")

        self.search_worker = SearchWorker(self.engine, query, year_param, search_type, mode, parent_id, season_num)
        # Use QueuedConnection for safety
        self.search_worker.results_found.connect(self._on_search_results, Qt.QueuedConnection)
        self.search_worker.start()

    @Slot(list, str)
    def _on_search_results(self, results, mode):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search API")
        self.results_list.clear()
        
        for res in results:
            if res['media_type'] == 'tv': icon = "📺"
            elif res['media_type'] == 'season': icon = "📂"
            elif res['media_type'] == 'episode': icon = "📄"
            else: icon = "🎬"
            
            label = f"{icon} {res['title']}"
            if res.get('year'): label += f" ({res['year']})"
            if res.get('episode_count'): label += f" [{res['episode_count']} eps]"
            
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, res)
            self.results_list.addItem(item)
            
        if not results:
            self.results_list.addItem("No matches found.")

    def _on_item_double_clicked(self, item):
        res = item.data(Qt.UserRole)
        if not res: return
        
        if res['media_type'] == 'tv':
            self.nav_stack.append(("search", None, None, "Search Results"))
            self._on_search(mode="seasons", parent_id=res['tmdb_id'], title=res['title'])
        elif res['media_type'] == 'season':
            self.nav_stack.append(("seasons", res['show_id'], None, self.nav_label.text()))
            self._on_search(mode="episodes", parent_id=res['show_id'], season_num=res['season_number'], title=res['title'])
        elif res['media_type'] == 'episode' or res['media_type'] == 'movie':
            self._on_action_clicked()

    def _on_back(self):
        if not self.nav_stack: return
        mode, parent_id, season_num, title = self.nav_stack.pop()
        self._on_search(mode=mode, parent_id=parent_id, season_num=season_num, title=title)

    def _on_selection_changed(self):
        items = self.results_list.selectedItems()
        if not items: 
            self.action_btn.setEnabled(False)
            return
        
        res = items[0].data(Qt.UserRole)
        if not res: return
        self.selected_media = res
        self.action_btn.setEnabled(True)
        
        self.preview_title.setText(res['title'])
        meta = f"Type: {res['media_type'].capitalize()}"
        if res.get('year'): meta += f" | Year: {res['year']}"
        self.preview_meta.setText(meta)
        self.preview_overview.setText(res.get('overview', ""))
        
        if res.get('poster_path'):
            self._load_poster(res['poster_path'])
        else:
            self.preview_poster.setText("No Poster")

    def _load_poster(self, poster_path):
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(base_dir, 'data', 'cache', 'posters')
        local_path = os.path.join(cache_dir, poster_path.lstrip('/'))

        if hasattr(self, 'poster_worker') and self.poster_worker.isRunning():
            try:
                self.poster_worker.finished.disconnect()
                self.poster_worker.terminate()
                self.poster_worker.wait()
            except: pass

        if os.path.exists(local_path):
            self._on_poster_loaded(QPixmap(local_path))
            return

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

    def _add_to_basket(self):
        if not self.selected_media: return
        m = self.selected_media
        
        if self.basket:
            first_type = self.basket[0]['media']['media_type']
            # Allow mixing season/episode/tv for TV, but not movie with TV
            b_is_tv = first_type in ('tv', 'season', 'episode')
            m_is_tv = m['media_type'] in ('tv', 'season', 'episode')
            if b_is_tv != m_is_tv: return

        # Capture S/E from context or override
        s = m.get('season_number', self.season_spin.value())
        e = m.get('episode_number', self.episode_spin.value())
        
        self.basket.append({'media': m, 's': s, 'e': e})
        self._refresh_basket_ui()

    def _remove_from_basket(self):
        idx = self.basket_list.currentRow()
        if idx >= 0:
            self.basket.pop(idx)
            self._refresh_basket_ui()

    def _clear_basket(self):
        self.basket = []
        self._refresh_basket_ui()

    def _refresh_basket_ui(self):
        self.basket_list.clear()
        for item in self.basket:
            m = item['media']
            label = f"{m['title']}"
            if m['media_type'] in ('tv', 'season', 'episode'):
                label += f" [S{str(item['s']).zfill(2)}E{str(item['e']).zfill(2)}]"
            self.basket_list.addItem(label)
        
        # Centralized state management
        has_items = len(self.basket) > 0
        self.confirm_btn.setEnabled(has_items)
        self.type_combo.setEnabled(not has_items)

    def _on_confirm(self):
        if not self.basket: return
        self.engine.db.clear_match(self.file_id)
        all_episodes = []
        last_s, last_type = None, None
        
        for item in self.basket:
            res = item['media']
            # Important: if the item is an 'episode', we must treat it as 'tv' media type for the resolver
            actual_res = res.copy()
            if res['media_type'] in ('episode', 'season'):
                actual_res['media_type'] = 'tv'
                # Ensure tmdb_id is the show ID for store_result
                actual_res['tmdb_id'] = res.get('show_id', res['tmdb_id'])

            s_num, e_num = item['s'], item['e']
            last_s, last_type = s_num, actual_res['media_type']
            all_episodes.append(e_num)
            
            vid_mock = self.engine.db.get_file_by_id(self.file_id)
            vid_mock['fn_season'], vid_mock['fn_episode'], vid_mock['fn_media_type'] = s_num, str(e_num), actual_res['media_type']
            
            mid = self.engine.resolver._store_result(actual_res)
            self.engine.resolver._finalize_match(self.file_id, mid, actual_res, vid_mock, status='matched')
            
        ep_val = str(all_episodes[0]) if len(all_episodes) == 1 else str(sorted(list(set(all_episodes))))
        self.engine.db.update_file(self.file_id, fn_season=last_s, fn_episode=ep_val, fn_media_type=last_type)
        self.accept()
