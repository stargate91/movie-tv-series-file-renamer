from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QWidget, QComboBox, QScrollArea, QFrame, QGridLayout, QCheckBox)
from PySide6.QtCore import Qt, Signal
from ui.widgets.image_widgets import ImageLoader
import os

class SelectionDialog(QDialog):
    def __init__(self, parent, pipeline, meta):
        super().__init__(parent)
        self.pipeline = pipeline
        self.meta = meta
        self.selected_item = None
        
        # Navigation State
        self.view_mode = "search" # "search", "seasons", "episodes"
        self.current_series = None
        self.current_season = None
        self.results_data = []
        
        self.setWindowTitle("Intelligent Metadata Resolver")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- NAVIGATION BREADCRUMBS ---
        self.nav_container = QWidget()
        self.nav_bar = QHBoxLayout(self.nav_container)
        self.nav_bar.setContentsMargins(0, 0, 0, 0)
        self.nav_bar.setSpacing(8)
        
        self.nav_root = QPushButton("🔍 Search Results")
        self.nav_root.setObjectName("NavBtn")
        self.nav_root.setCursor(Qt.PointingHandCursor)
        self.nav_root.clicked.connect(self.go_back_to_search)
        
        self.nav_sep1 = QLabel("›")
        self.nav_sep1.setStyleSheet("color: #94a3b8; font-size: 18px;")
        
        self.nav_series = QPushButton("Series Name")
        self.nav_series.setObjectName("NavBtn")
        self.nav_series.setCursor(Qt.PointingHandCursor)
        self.nav_series.clicked.connect(self.go_back_to_seasons)
        
        self.nav_sep2 = QLabel("›")
        self.nav_sep2.setStyleSheet("color: #94a3b8; font-size: 18px;")
        
        self.nav_season = QLabel("Season X")
        self.nav_season.setStyleSheet("font-weight: bold; color: #334155;")

        self.nav_bar.addWidget(self.nav_root)
        self.nav_bar.addWidget(self.nav_sep1)
        self.nav_bar.addWidget(self.nav_series)
        self.nav_bar.addWidget(self.nav_sep2)
        self.nav_bar.addWidget(self.nav_season)
        self.nav_bar.addStretch()
        
        layout.addWidget(self.nav_container)

        # --- TOP SEARCH BAR ---
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_frame.setStyleSheet("QFrame#HeaderFrame { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; }")
        header_layout = QHBoxLayout(header_frame)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Movie", "TV Show", "Extra"])
        self.type_combo.setFixedWidth(110)
        
        current_type = meta.get('file_type', 'movie')
        self.type_combo.setCurrentText("Extra" if current_type == 'extra' else ("Movie" if current_type == 'movie' else "TV Show"))
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        
        self.search_input = QLineEdit()
        guessed_title = meta.get('extras', {}).get('title', '')
        self.search_input.setText(guessed_title)
        self.search_input.setPlaceholderText("Enter title to search...")
        self.search_input.returnPressed.connect(self.perform_search)

        # Year Input (Movies)
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("Year")
        self.year_input.setFixedWidth(60)
        guessed_year = meta.get('extras', {}).get('year', '')
        self.year_input.setText(str(guessed_year) if guessed_year and guessed_year != 'unknown' else "")
        self.year_input.returnPressed.connect(self.perform_search)

        # TV Context (S/E)
        self.tv_context = QWidget()
        tv_ctx_layout = QHBoxLayout(self.tv_context)
        tv_ctx_layout.setContentsMargins(0,0,0,0)
        
        self.season_input = QLineEdit()
        self.season_input.setPlaceholderText("S")
        self.season_input.setFixedWidth(40)
        s_val = meta.get('season_file') or meta.get('season_folder')
        self.season_input.setText(str(s_val) if s_val != 'unknown' else "")

        self.episode_input = QLineEdit()
        self.episode_input.setPlaceholderText("E")
        self.episode_input.setFixedWidth(40)
        e_val = meta.get('episode_file') or meta.get('episode_folder')
        self.episode_input.setText(str(e_val) if e_val != 'unknown' else "")

        tv_ctx_layout.addWidget(QLabel("S:"))
        tv_ctx_layout.addWidget(self.season_input)
        tv_ctx_layout.addWidget(QLabel("E:"))
        tv_ctx_layout.addWidget(self.episode_input)

        self.search_btn = QPushButton("🔍 Search")
        self.search_btn.setObjectName("PrimaryBtn")
        self.search_btn.setFixedWidth(100)
        self.search_btn.clicked.connect(self.perform_search)

        header_layout.addWidget(self.type_combo)
        header_layout.addWidget(self.search_input, 1)
        header_layout.addWidget(self.year_input)
        header_layout.addWidget(self.tv_context)
        header_layout.addWidget(self.search_btn)
        layout.addWidget(header_frame)

        # --- EXTRAS SPECIFIC UI ---
        self.extra_container = QWidget()
        extra_layout = QVBoxLayout(self.extra_container)
        extra_layout.setContentsMargins(0, 10, 0, 10)
        
        ex_top = QHBoxLayout()
        self.extra_type_combo = QComboBox()
        from metadata.classifier import EXTRA_TYPE_MAP
        self.extra_type_combo.addItems(list(EXTRA_TYPE_MAP.values()))
        self.extra_type_combo.setCurrentText(meta.get('extra_type', 'Sample'))
        self.extra_type_combo.currentTextChanged.connect(self.update_extra_preview)
        
        self.link_btn = QPushButton("🔗 Link to Parent Content...")
        self.link_btn.setObjectName("SecondaryBtn")
        self.link_btn.clicked.connect(self.manual_link_parent)
        
        ex_top.addWidget(QLabel("Extra Type:"))
        ex_top.addWidget(self.extra_type_combo)
        ex_top.addSpacing(20)
        ex_top.addWidget(self.link_btn)
        ex_top.addStretch()
        extra_layout.addLayout(ex_top)

        self.parent_info_lbl = QLabel("<i>Unlinked Extra</i>")
        self.parent_info_lbl.setStyleSheet("color: #6366f1; font-size: 12px; padding: 5px;")
        extra_layout.addWidget(self.parent_info_lbl)

        self.extra_preview_lbl = QLabel("")
        self.extra_preview_lbl.setStyleSheet("""
            QLabel { 
                color: #059669; font-weight: bold; font-size: 12px; 
                padding: 15px; border: 1px dashed #059669; border-radius: 8px; background: #f0fdf4; 
            }
        """)
        extra_layout.addWidget(self.extra_preview_lbl)
        
        layout.addWidget(self.extra_container)

        # --- RESULTS SCROLL AREA ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.scroll_content = QWidget()
        self.results_layout = QVBoxLayout(self.scroll_content)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.results_layout.setSpacing(10)
        self.scroll.setWidget(self.scroll_content)
        
        layout.addWidget(self.scroll)

        # --- FOOTER ---
        footer_layout = QHBoxLayout()
        self.status_info = QLabel("Ready")
        self.status_info.setStyleSheet("color: #64748b; font-size: 11px;")
        footer_layout.addWidget(self.status_info)
        footer_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)
        
        self.confirm_btn = QPushButton("✅ Confirm")
        self.confirm_btn.setObjectName("PrimaryBtn")
        self.confirm_btn.clicked.connect(self.accept_selection)
        footer_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(footer_layout)

        # Initial Styles
        self.setStyleSheet("""
            QPushButton#NavBtn { 
                background: transparent; color: #6366f1; border: none; 
                font-weight: bold; text-decoration: underline; padding: 2px;
            }
            QPushButton#NavBtn:hover { color: #4338ca; }
            QLabel#NavLabel { color: #1e293b; font-weight: bold; }
        """)

        self.on_type_changed()
        if guessed_title:
            self.perform_search()

    def on_type_changed(self):
        t = self.type_combo.currentText()
        is_extra = t == "Extra"
        
        self.year_input.setVisible(t in ["Movie", "TV Show"])
        self.tv_context.setVisible(t == "TV Show")
        self.search_input.setVisible(not is_extra)
        self.search_btn.setVisible(not is_extra)
        
        self.extra_container.setVisible(is_extra)
        self.scroll.setVisible(not is_extra)
        self.nav_container.setVisible(not is_extra and self.view_mode != "search")
        
        if is_extra:
            self.update_parent_label()
            self.update_extra_preview()
            self.confirm_btn.setEnabled(True)
        else:
            self.confirm_btn.setEnabled(False) # Require selection for other types
            self.go_back_to_search()

    def update_parent_label(self):
        parent = self.meta.get('extra_parent')
        if parent:
            self.parent_info_lbl.setText(f"<b>🔗 Linked to:</b> {parent}")
        else:
            self.parent_info_lbl.setText("<i>⚠️ Unlinked Extra (Rename might fail or use default)</i>")

    def manual_link_parent(self):
        # Filter for non-extra files in current state
        main_files = [p for p, m in self.pipeline.metadata_map.items() if m.get('file_type') != 'extra']
        if not main_files:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Parent Found", "Please analyze some movies or episodes first to link this extra to them.")
            return
        
        from ui.dialogs.parent_selection_dialog import ParentSelectionDialog
        dialog = ParentSelectionDialog(self, main_files)
        if dialog.exec():
            parent_abs = dialog.selected_parent
            self.meta['extra_parent'] = os.path.basename(parent_abs)
            self.update_parent_label()
            self.update_extra_preview()

    def update_extra_preview(self):
        from core.renamer import format_filename
        parent = self.meta.get('extra_parent') or 'ParentTitle'
        tmpl = self.pipeline.s.extra_template
        e_type = self.extra_type_combo.currentText()
        orig_base = os.path.splitext(os.path.basename(self.meta.get('file_path', '')))[0]
        
        raw_name = tmpl.replace("{parent}", parent).replace("{extra_type}", e_type).replace("{original}", orig_base)
        formatted = format_filename(raw_name, self.pipeline.s.filename_case, self.pipeline.s.separator)
        ext = os.path.splitext(self.meta.get('file_path', ''))[1]
        
        self.extra_preview_lbl.setText(f"FUTURE FILENAME: {formatted}{ext}")

    def update_nav(self):
        self.nav_container.setVisible(self.view_mode != "search")
        self.nav_sep1.setVisible(self.view_mode in ["seasons", "episodes"])
        self.nav_series.setVisible(self.view_mode in ["seasons", "episodes"])
        self.nav_sep2.setVisible(self.view_mode == "episodes")
        self.nav_season.setVisible(self.view_mode == "episodes")
        
        if self.current_series:
            name = self.current_series.get('name') or self.current_series.get('title')
            self.nav_series.setText(name[:30] + "..." if len(name) > 30 else name)
        if self.current_season:
            self.nav_season.setText(f"Season {self.current_season}")

    def clear_results(self):
        for i in reversed(range(self.results_layout.count())): 
            w = self.results_layout.itemAt(i).widget()
            if w: w.setParent(None)

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query: return
        
        self.status_info.setText("Searching...")
        self.view_mode = "search"
        self.update_nav()
        self.clear_results()
        
        t = self.type_combo.currentText()
        year = self.year_input.text().strip() or None
        lang = self.pipeline.s.metadata_language
        
        try:
            if t == "Movie":
                res = self.pipeline.api.get_from_tmdb_movie(query, year, language=lang)
                self.display_main_results(res.get('results', []) if res else [])
            elif t == "TV Show":
                res = self.pipeline.api.get_from_tmdb_tv(query, year, language=lang)
                self.display_main_results(res.get('results', []) if res else [])
            else:
                # Fallback for Extras or other types
                self.status_info.setText("Search not applicable for this type.")
        except Exception as e:
            self.status_info.setText(f"Search error: {str(e)}")

    def display_main_results(self, results):
        self.clear_results()
        self.results_data = results
        
        if not results:
            self.status_info.setText("No results found. Try a different title or year.")
            no_res = QLabel("No results found.")
            no_res.setAlignment(Qt.AlignCenter)
            no_res.setStyleSheet("color: #94a3b8; font-size: 14px; margin-top: 50px;")
            self.results_layout.addWidget(no_res)
            return

        # Grid Layout for Movies/Series
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(20)
        grid.setContentsMargins(0, 0, 0, 0)
        
        cols = 4
        for i, res in enumerate(results):
            card = self.create_result_card(res)
            grid.addWidget(card, i // cols, i % cols)
            
        self.results_layout.addWidget(grid_widget)
        self.status_info.setText(f"Found {len(results)} results")

    def create_result_card(self, data):
        card = QFrame()
        card.setObjectName("ResultCard")
        card.setFixedSize(180, 280)
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet("""
            QFrame#ResultCard { background: white; border: 1px solid #e2e8f0; border-radius: 10px; }
            QFrame#ResultCard:hover { border-color: #6366f1; background: #f5f3ff; }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(5, 5, 5, 5)
        
        p_path = data.get('poster_path')
        url = f"https://image.tmdb.org/t/p/w300{p_path}" if p_path else None
        poster = ImageLoader(url, 170, 220)
        layout.addWidget(poster)
        
        title = data.get('title') or data.get('name', 'Unknown')
        year = (data.get('release_date') or data.get('first_air_date') or "")[:4]
        
        lbl = QLabel(f"<b>{title}</b><br><small>{year}</small>")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 11px; color: #1e293b;")
        layout.addWidget(lbl)
        
        # Click handling
        card.mousePressEvent = lambda e: self.on_main_result_clicked(data)
        return card

    def on_main_result_clicked(self, data):
        if self.type_combo.currentText() == "Movie":
            self.selected_item = data
            self.accept()
            return
            
        # TV Show logic
        self.current_series = data
        s_val = self.season_input.text().strip()
        e_val = self.episode_input.text().strip()
        
        if s_val and e_val:
            # SHORTCUT: Directly try to get the episode
            try:
                lang = self.pipeline.s.metadata_language
                self.status_info.setText("Directly fetching episode...")
                season_data = self.pipeline.api.get_from_tmdb_season(data['id'], s_val, language=lang)
                episodes = season_data.get('episodes', [])
                for ep in episodes:
                    if str(ep.get('episode_number')) == e_val:
                        # Inject series info for the model
                        ep['series_name'] = data.get('name')
                        ep['series_poster_path'] = data.get('poster_path')
                        ep['file_type'] = 'episode'
                        self.selected_item = ep
                        self.accept()
                        return
            except: pass
        
        # If no shortcut or shortcut failed, go to Seasons
        self.view_seasons(data)

    def view_seasons(self, series_data):
        self.view_mode = "seasons"
        self.current_series = series_data
        self.update_nav()
        self.clear_results()
        
        # In TMDB, we need full details to get season list correctly
        self.status_info.setText("Loading seasons...")
        try:
            lang = self.pipeline.s.metadata_language
            full_data = self.pipeline.api.get_tv_show_details(series_data['id'], language=lang)
            seasons = full_data.get('seasons', [])
            
            # Show All Episodes Button
            show_all_btn = QPushButton("📜 View All Episodes (Flattened List)")
            show_all_btn.setObjectName("SecondaryBtn")
            show_all_btn.setMinimumHeight(40)
            show_all_btn.setCursor(Qt.PointingHandCursor)
            show_all_btn.clicked.connect(self.view_all_episodes)
            self.results_layout.addWidget(show_all_btn)

            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setSpacing(15)
            
            for i, s in enumerate(seasons):
                s_num = s.get('season_number')
                
                card = QFrame()
                card.setObjectName("SeasonCard")
                card.setFixedSize(140, 210)
                card.setCursor(Qt.PointingHandCursor)
                card.setStyleSheet("""
                    QFrame#SeasonCard { background: white; border: 1px solid #e2e8f0; border-radius: 8px; }
                    QFrame#SeasonCard:hover { border-color: #6366f1; background: #f5f3ff; }
                """)
                c_layout = QVBoxLayout(card)
                c_layout.setContentsMargins(5, 5, 5, 5)
                
                p_path = s.get('poster_path')
                url = f"https://image.tmdb.org/t/p/w200{p_path}" if p_path else None
                poster = ImageLoader(url, 130, 170)
                c_layout.addWidget(poster)
                
                name = s.get('name', f"Season {s_num}")
                lbl = QLabel(f"<b>{name}</b>")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("font-size: 10px; color: #1e293b;")
                c_layout.addWidget(lbl)
                
                card.mousePressEvent = lambda e, sn=s_num: self.view_episodes(sn)
                grid.addWidget(card, i // 5, i % 5)
                
            self.results_layout.addWidget(grid_widget)
            self.status_info.setText(f"Select a season for {series_data.get('name')}")
        except Exception as e:
            self.status_info.setText(f"Error loading seasons: {e}")

    def on_season_selected_bulk(self, season_num):
        # Create a partial metadata object for the entire selection
        data = self.current_series.copy()
        data['season_number'] = season_num
        data['episode_number'] = 'unknown' # Crucial: mark as unknown for later distribution
        data['is_season_only'] = True
        
        # We wrap it in a way that finalize_selection or controllers understand
        self.selected_item = data
        self.accept()

    def add_episode_row(self, ep):
        ep_row = QFrame()
        ep_row.setObjectName("EpisodeRow")
        ep_row.setStyleSheet("""
            QFrame#EpisodeRow { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 5px; }
            QFrame#EpisodeRow:hover { border-color: #6366f1; background: #f8fafc; }
        """)
        row_layout = QHBoxLayout(ep_row)
        
        # Checkbox for multi-select
        cb = QCheckBox()
        cb.setFixedWidth(30)
        cb.setStyleSheet("QCheckBox::indicator { width: 20px; height: 20px; }")
        row_layout.addWidget(cb)
        ep_row.checkbox = cb # Store reference for get_checked_episodes
        
        # Thumbnail
        still_path = ep.get('still_path')
        thumb_url = f"https://image.tmdb.org/t/p/w300{still_path}" if still_path else None
        thumb = ImageLoader(thumb_url, 120, 68)
        thumb.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 4px;")
        row_layout.addWidget(thumb)
        
        info = QVBoxLayout()
        s_num = ep.get('season_number', self.current_season or 0)
        e_num = ep.get('episode_number', 0)
        title_lbl = QLabel(f"<b>S{s_num:02d}E{e_num:02d} - {ep.get('name')}</b>")
        info.addWidget(title_lbl)
        
        desc = ep.get('overview', 'No description available.')
        desc_lbl = QLabel(desc[:120] + "..." if len(desc) > 120 else desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        info.addWidget(desc_lbl)
        
        row_layout.addLayout(info, 1)
        
        ep_row.metadata = ep
        ep_row.mousePressEvent = lambda e, d=ep: self.on_episode_selected(d)
        self.results_layout.addWidget(ep_row)

    def view_episodes(self, season_num):
        self.view_mode = "episodes"
        self.current_season = season_num
        self.update_nav()
        self.clear_results()
        
        self.status_info.setText(f"Loading episodes for Season {season_num}...")
        try:
            lang = self.pipeline.s.metadata_language
            season_data = self.pipeline.api.get_from_tmdb_season(self.current_series['id'], season_num, language=lang)
            episodes = season_data.get('episodes', [])
            
            # Bulk Season Button
            bulk_btn = QPushButton(f"🎯 Use 'Season {season_num}' for All Selected Files")
            bulk_btn.setObjectName("PrimaryBtn")
            bulk_btn.setMinimumHeight(40)
            bulk_btn.clicked.connect(lambda: self.on_season_selected_bulk(season_num))
            self.results_layout.addWidget(bulk_btn)
            
            for ep in episodes:
                self.add_episode_row(ep)
                
            self.confirm_btn.setEnabled(True)
            self.status_info.setText(f"Select episodes from Season {season_num}")
        except Exception as e:
            self.status_info.setText(f"Error: {e}")

    def view_all_episodes(self):
        from PySide6.QtWidgets import QApplication
        self.view_mode = "episodes" # Use episodes mode for nav and confirm logic
        self.update_nav()
        self.clear_results()
        
        self.status_info.setText("Loading ALL episodes... Please wait.")
        QApplication.processEvents()
        
        try:
            lang = self.pipeline.s.metadata_language
            full_data = self.pipeline.api.get_tv_show_details(self.current_series['id'], language=lang)
            seasons = full_data.get('seasons', [])
            
            for s in seasons:
                s_num = s.get('season_number')
                if s_num is None: continue
                self.status_info.setText(f"Fetching Season {s_num}...")
                QApplication.processEvents()
                s_data = self.pipeline.api.get_from_tmdb_season(self.current_series['id'], s_num, language=lang)
                for ep in s_data.get('episodes', []):
                    self.add_episode_row(ep)
            
            self.confirm_btn.setEnabled(True)
            self.status_info.setText("All episodes loaded. Select as needed.")
        except Exception as e:
            self.status_info.setText(f"Error: {e}")

    def on_episode_selected(self, ep_data):
        # If no checkboxes are checked, behave like a single selection
        selected = self.get_checked_episodes()
        if not selected:
            self.finalize_selection([ep_data])
        else:
            # If checkboxes are used, the user must use the Confirm button
            pass

    def get_checked_episodes(self):
        selected = []
        for i in range(self.results_layout.count()):
            item = self.results_layout.itemAt(i).widget()
            if hasattr(item, 'checkbox') and item.checkbox.isChecked():
                # Extract data from the row (we need to store it)
                # For simplicity, let's store the data on the row widget
                if hasattr(item, 'metadata'):
                    selected.append(item.metadata)
        return selected

    def finalize_selection(self, items):
        if not items: return
        
        # Inject parent info to all selected items
        for item in items:
            item['series_name'] = self.current_series.get('name')
            item['series_poster_path'] = self.current_series.get('poster_path')
            item['file_type'] = 'episode'
        
        # If it's multiple, we return the list
        self.selected_item = items if len(items) > 1 else items[0]
        self.accept()

    def go_back_to_search(self):
        self.view_mode = "search"
        self.current_series = None
        self.current_season = None
        self.confirm_btn.setEnabled(self.type_combo.currentText() == "Extra")
        self.update_nav()
        if self.results_data:
            self.display_main_results(self.results_data)
        else:
            self.perform_search()

    def go_back_to_seasons(self):
        if self.current_series:
            self.view_seasons(self.current_series)

    def accept_selection(self):
        if self.type_combo.currentText() == "Extra":
            self.selected_item = {
                'file_type': 'extra',
                'extra_type': self.extra_type_combo.currentText(),
                'extra_parent': self.meta.get('extra_parent'),
                'title': os.path.basename(self.meta.get('file_path', ''))
            }
            self.accept()
            return

        if self.view_mode == "episodes":
            selected = self.get_checked_episodes()
            if selected:
                self.finalize_selection(selected)
                return
        
        # If we are in search or seasons, and they hit confirm without clicking a card
        # maybe we don't do anything or take the first one?
        if self.selected_item:
            self.accept()
