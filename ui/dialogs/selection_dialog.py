from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem, QWidget, QComboBox, QCheckBox
from PySide6.QtCore import Qt
from ui.components.image_widgets import ImageLoader
import re

class SelectionDialog(QDialog):
    def __init__(self, parent, pipeline, meta):
        super().__init__(parent)
        self.pipeline = pipeline
        self.meta = meta
        self.selected_item = None
        
        self.setWindowTitle("Select Metadata")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Type Selector
        type_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Movie", "TV Show"])
        self.type_combo.setCurrentText("Movie" if meta.get('file_type') == 'movie' else "TV Show")
        self.type_combo.currentTextChanged.connect(self.toggle_tv_fields)
        type_layout.addWidget(QLabel("Type:"))
        type_layout.addWidget(self.type_combo)
        
        # Season/Episode (TV Only)
        self.tv_fields = QWidget()
        tv_layout = QHBoxLayout(self.tv_fields)
        tv_layout.setContentsMargins(0, 0, 0, 0)
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
        
        tv_layout.addWidget(QLabel("S:"))
        tv_layout.addWidget(self.season_input)
        tv_layout.addWidget(QLabel("E:"))
        tv_layout.addWidget(self.episode_input)
        type_layout.addWidget(self.tv_fields)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Search Box
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        guessed_title = meta.get('extras', {}).get('title', '')
        self.search_input.setText(guessed_title)
        self.search_input.setPlaceholderText("Title...")
        self.search_input.returnPressed.connect(self.perform_search)
        
        self.year_input = QLineEdit()
        guessed_year = meta.get('extras', {}).get('year', '')
        self.year_input.setText(str(guessed_year) if guessed_year and guessed_year != 'unknown' else "")
        self.year_input.setPlaceholderText("Year")
        self.year_input.setFixedWidth(60)
        self.year_input.returnPressed.connect(self.perform_search)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.setObjectName("PrimaryBtn")
        search_btn.clicked.connect(self.perform_search)
        
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.year_input)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)
        
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("✅ Select")
        ok_btn.setObjectName("PrimaryBtn")
        ok_btn.clicked.connect(self.accept_selection)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
        self.toggle_tv_fields(self.type_combo.currentText())
        
        # Initial search if we have a title
        if guessed_title:
            self.perform_search()

    def toggle_tv_fields(self, search_type):
        self.tv_fields.setVisible(search_type == "TV Show")

    def perform_search(self):
        raw_query = self.search_input.text().strip()
        if not raw_query: return
        
        query = raw_query.replace(".", " ").replace("_", " ")
        year = self.year_input.text().strip() or None
        search_type = self.type_combo.currentText()
        s = self.season_input.text().strip()
        e = self.episode_input.text().strip()

        try:
            if search_type == "Movie":
                res = self.pipeline.api.get_from_tmdb_movie(query, year)
                self.display_results(res.get('results', []) if res else [])
            else:
                # TV Search
                res = self.pipeline.api.get_from_tmdb_tv(query, year)
                series_results = res.get('results', []) if res else []
                
                # If Season is provided, let's be smart and list episodes of the first match
                if s and series_results:
                    top_series = series_results[0]
                    try:
                        season_data = self.pipeline.api.get_tv_season_details(top_series['id'], s)
                        if season_data and 'episodes' in season_data:
                            # We show episodes instead of series
                            episodes = season_data['episodes']
                            # Enrich episodes with series context for later
                            for ep in episodes:
                                ep['series_name'] = top_series.get('name')
                                ep['series_poster_path'] = top_series.get('poster_path')
                                ep['season_poster_path'] = season_data.get('poster_path')
                                s_year = season_data.get('air_date', '')[:4]
                                ep['season_year_range'] = f"({s_year})" if s_year else ""
                                ep['file_type'] = 'episode' # Mark as episode
                                
                            self.display_results(episodes)
                            
                            # If E is also provided, try to pre-select it
                            if e:
                                for i in range(self.list_widget.count()):
                                    item = self.list_widget.item(i)
                                    data = item.data(Qt.UserRole)
                                    if str(data.get('episode_number')) == str(e):
                                        self.list_widget.setCurrentItem(item)
                                        break
                            return
                    except: pass
                
                self.display_results(series_results)

        except Exception as ex:
            self.list_widget.clear()
            self.list_widget.addItem(f"Error: {str(ex)}")

    def display_results(self, results):
        self.list_widget.clear()
        for res in results:
            is_ep = 'episode_number' in res
            p_path = res.get('still_path') if is_ep else res.get('poster_path')
            url = f"https://image.tmdb.org/t/p/w200{p_path}" if p_path else None
            
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            
            # Checkbox for multi-selection (only for episodes)
            cb = QCheckBox()
            cb.setVisible(is_ep)
            item_layout.addWidget(cb)
            
            poster = ImageLoader(url, 60 if is_ep else 40, 40 if is_ep else 60)
            item_layout.addWidget(poster)
            
            if is_ep:
                title = f"E{res.get('episode_number'):02d} - {res.get('name')}"
                date = res.get('air_date', '')
            else:
                title = res.get('title') or res.get('name', 'Unknown')
                date = res.get('release_date') or res.get('first_air_date', '')
                
            lbl = QLabel(f"<b>{title}</b> ({date[:4]})<br><small>{res.get('overview', '')[:100]}...</small>")
            lbl.setWordWrap(True)
            item_layout.addWidget(lbl, 1)
            
            list_item = QListWidgetItem(self.list_widget)
            list_item.setData(Qt.UserRole, res)
            list_item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)

    def accept_selection(self):
        # Check for multiple selections via checkboxes
        selected_data = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    selected_data.append(item.data(Qt.UserRole))
        
        # If nothing checked via checkbox, take the current highlighted item
        if not selected_data:
            curr = self.list_widget.currentItem()
            if curr:
                selected_data = [curr.data(Qt.UserRole)]
        
        if not selected_data: return
        
        if len(selected_data) > 1:
            # Combine multiple episodes
            first = selected_data[0]
            combined = first.copy()
            ep_nums = [str(d.get('episode_number')) for d in selected_data]
            titles = [d.get('name') for d in selected_data]
            
            combined['episode_number'] = ep_nums # List of numbers
            combined['name'] = " & ".join(titles)
            combined['is_combined'] = True
            self.selected_item = combined
            self.accept()
            return
            
        data = selected_data[0]
        # If it's already an episode from the list, we're done
        if 'episode_number' in data:
            self.selected_item = data
            self.accept()
            return

        search_type = self.type_combo.currentText()
        if search_type == "TV Show":
            s = self.season_input.text().strip()
            e = self.episode_input.text().strip()
            
            if s:
                try:
                    # Case 1: Both S and E provided -> Full Episode Detail
                    if e:
                        ep_data = self.pipeline.api.get_tv_episode_details(data['id'], s, e)
                        if ep_data and 'id' in ep_data:
                            ep_data['series_poster_path'] = data.get('poster_path')
                            ep_data['series_name'] = data.get('name')
                            
                            season_data = self.pipeline.api.get_tv_season_details(data['id'], s)
                            if season_data:
                                ep_data['season_poster_path'] = season_data.get('poster_path')
                                s_year = season_data.get('air_date', '')[:4]
                                ep_data['season_year_range'] = f"({s_year})" if s_year else ""
                            
                            self.selected_item = ep_data
                            self.accept()
                            return
                    
                    # Case 2: Only S provided -> Season Level Enrichment
                    else:
                        season_data = self.pipeline.api.get_tv_season_details(data['id'], s)
                        if season_data:
                            # We wrap it to look like an episode result but with season info
                            enriched = data.copy()
                            enriched['season_number'] = int(s)
                            enriched['season_poster_path'] = season_data.get('poster_path')
                            enriched['series_poster_path'] = data.get('poster_path')
                            enriched['series_name'] = data.get('name')
                            s_year = season_data.get('air_date', '')[:4]
                            enriched['season_year_range'] = f"({s_year})" if s_year else ""
                            
                            self.selected_item = enriched
                            self.accept()
                            return
                except: pass

        self.selected_item = data
        self.accept()
