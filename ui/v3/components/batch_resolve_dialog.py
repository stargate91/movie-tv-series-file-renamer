import logging
from PySide6.QtCore import Qt, QSize, Signal, Slot
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QWidget,
                             QPushButton, QListWidget, QListWidgetItem, QLabel, QFrame, 
                             QScrollArea, QSpinBox, QMessageBox, QAbstractItemView, QComboBox)
from PySide6.QtGui import QPixmap

from ui.v3.styles.theme import Theme
from core.i18n import T
from ui.v3.components.image_loader import ImageDownloader
from .manual_resolve.searcher import SearchWorker
from .manual_resolve.tv_selector import TVMetadataSelector
from .manual_resolve.result_widget import ResultItemWidget

logger = logging.getLogger(__name__)

class BatchResolveDialog(QDialog):
    """
    Dedicated dialog for identifying multiple files at once via TMDB.
    Supports Series, Season, and Episode level identification with auto-part numbering.
    """
    def __init__(self, engine, selected_files, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.selected_files = selected_files
        self.selected_media = None
        self.search_worker = None
        self.nav_stack = [] 

        self.setWindowTitle(T("discovery.batch_resolve.title", count=len(selected_files)))
        self.setMinimumSize(1100, 800)
        self.setStyleSheet(Theme.get_main_stylesheet())
        
        self._init_ui()
        self._populate_file_list()
        self._prefill_search()

    def _init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # --- LEFT PANE: File Order ---
        left_pane = QWidget()
        left_pane.setFixedWidth(300)
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(T("discovery.batch_resolve.arrange_order"))
        lbl.setStyleSheet(Theme.get_card_header_style())
        left_layout.addWidget(lbl)
        
        self.file_list = QListWidget()
        self.file_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.file_list.setDefaultDropAction(Qt.MoveAction)
        self.file_list.setStyleSheet(Theme.get_sidebar_list_style())
        left_layout.addWidget(self.file_list)
        
        hint = QLabel(T("discovery.batch_resolve.drag_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(Theme.get_hint_style())
        left_layout.addWidget(hint)
        
        self.main_layout.addWidget(left_pane)

        # --- RIGHT PANE: API Search ---
        right_pane = QVBoxLayout()
        
        # Header / Nav
        nav_box = QHBoxLayout()
        self.back_btn = QPushButton(T("discovery.batch_resolve.back"))
        self.back_btn.setObjectName("SecondaryButton")
        self.back_btn.setFixedWidth(80)
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._on_back)
        
        self.nav_label = QLabel(T("discovery.batch_resolve.search_results"))
        self.nav_label.setStyleSheet(Theme.get_settings_title_style())
        
        nav_box.addWidget(self.back_btn)
        nav_box.addWidget(self.nav_label)
        nav_box.addStretch()
        right_pane.addLayout(nav_box)
        
        # Search Tools
        search_tools = QVBoxLayout()
        search_tools.setSpacing(10)
        
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("discovery.batch_resolve.search_placeholder"))
        self.search_input.setFixedHeight(40)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        
        # --- NEW: Year Filter ---
        self.year_input = QSpinBox()
        self.year_input.setRange(0, 2100)
        self.year_input.setValue(0)
        self.year_input.setSpecialValueText(T("manual_resolve.any_year"))
        self.year_input.setFixedWidth(100)
        self.year_input.setFixedHeight(40)
        self.year_input.setToolTip(T("manual_resolve.year_label"))
        
        # --- Search Type Selector ---
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItem(T("common.types.movie"), "movie")
        self.search_type_combo.addItem(T("common.types.tv"), "tv")
        self.search_type_combo.addItem(T("common.types.both"), "both")
        self.search_type_combo.setFixedWidth(130)
        self.search_type_combo.setFixedHeight(40)
        self.search_type_combo.currentIndexChanged.connect(self._on_search_type_changed)

        # --- TV Refinement (S/E) ---
        self.tv_selector = TVMetadataSelector()
        self.tv_selector.setVisible(False)
        
        self.search_btn = QPushButton(T("discovery.batch_resolve.search_btn"))
        self.search_btn.setFixedHeight(40)
        self.search_btn.setFixedWidth(100)
        self.search_btn.clicked.connect(self._on_search_clicked)
        
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.year_input)
        search_row.addWidget(self.tv_selector) # S/E in the search bar!
        search_row.addWidget(self.search_type_combo)
        search_row.addWidget(self.search_btn)
        search_tools.addLayout(search_row)
        
        right_pane.addLayout(search_tools)

        # Results & Preview Area
        content_row = QHBoxLayout()
        
        self.results_list = QListWidget()
        self.results_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        content_row.addWidget(self.results_list, 3)
        
        self.preview_panel = self._create_preview_panel()
        content_row.addWidget(self.preview_panel, 2)
        
        right_pane.addLayout(content_row)
        
        # TV Identification Options (Visible when TV/Season selected)
        self.tv_options_card = self._create_card(T("discovery.batch_resolve.tv_options"))
        self.tv_depth_combo = QComboBox()
        self.tv_depth_combo.addItem(T("discovery.batch_resolve.depth.series"), "series")
        self.tv_depth_combo.addItem(T("discovery.batch_operations.options.roles.episode"), "episode_sequential")
        self.tv_depth_combo.addItem(T("discovery.batch_operations.options.roles.bonus"), "extra") # Mapping extra/bonus logic
        self.tv_depth_combo.currentIndexChanged.connect(self._update_action_text)
        
        self.tv_options_card.layout().addWidget(QLabel(T("discovery.batch_resolve.match_depth")))
        self.tv_options_card.layout().addWidget(self.tv_depth_combo)
        self.tv_options_card.setVisible(False)
        right_pane.addWidget(self.tv_options_card)
        
        # Footer Action
        self.action_btn = QPushButton(T("discovery.batch_resolve.action_btn_default"))
        self.action_btn.setFixedHeight(50)
        self.action_btn.setEnabled(False)
        self.action_btn.setStyleSheet(Theme.get_primary_button_style())
        self.action_btn.clicked.connect(self._on_apply)
        right_pane.addWidget(self.action_btn)
        
        self.main_layout.addLayout(right_pane)

    def _create_card(self, title):
        card = QFrame()
        card.setStyleSheet(Theme.get_batch_card_style())
        layout = QVBoxLayout(card)
        if title:
            lbl = QLabel(title)
            lbl.setStyleSheet(Theme.get_preview_meta_style())
            layout.addWidget(lbl)
        return card

    def _create_preview_panel(self):
        panel = QFrame()
        panel.setStyleSheet(Theme.get_preview_panel_style())
        layout = QVBoxLayout(panel)
        
        self.preview_poster = QLabel(T("discovery.batch_resolve.no_selection"))
        self.preview_poster.setAlignment(Qt.AlignCenter)
        self.preview_poster.setFixedSize(200, 300)
        self.preview_poster.setStyleSheet(Theme.get_batch_card_style())
        
        self.preview_title = QLabel(T("discovery.batch_resolve.select_result"))
        self.preview_title.setWordWrap(True)
        self.preview_title.setStyleSheet(Theme.get_preview_title_style())
        
        self.preview_meta = QLabel("")
        self.preview_meta.setStyleSheet(Theme.get_preview_meta_style())
        
        self.preview_overview = QLabel("")
        self.preview_overview.setWordWrap(True)
        self.preview_overview.setStyleSheet(Theme.get_preview_overview_style())
        
        layout.addWidget(self.preview_poster, 0, Qt.AlignCenter)
        layout.addWidget(self.preview_title)
        layout.addWidget(self.preview_meta)
        layout.addWidget(self.preview_overview)
        layout.addStretch()
        return panel

    def _populate_file_list(self):
        for f in self.selected_files:
            item = QListWidgetItem(f['file_name'])
            item.setData(Qt.UserRole, f)
            item.setToolTip(f['file_name'])
            self.file_list.addItem(item)

    def _prefill_search(self):
        if not self.selected_files: return
        f = self.selected_files[0]
        title = f.get('fn_title') or f.get('fd_title') or ""
        self.search_input.setText(title)
        
        # Set search type hint
        mtype = f.get('fn_media_type') or f.get('category')
        if mtype == 'tv':
            idx = self.search_type_combo.findData('tv')
            if idx >= 0: self.search_type_combo.setCurrentIndex(idx)
        else:
            idx = self.search_type_combo.findData('movie')
            if idx >= 0: self.search_type_combo.setCurrentIndex(idx)

        if title:
            self._on_search_clicked()

    def _on_search_clicked(self, mode="search", parent_id=None, season_num=None, title=None):
        query = self.search_input.text().strip()
        if not query and mode == "search": return

        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.results_found.disconnect()
            self.search_worker.terminate()

        self.results_list.clear()
        self.results_list.addItem(T("discovery.batch_resolve.searching"))
        
        if mode == "search":
            self.nav_stack = []
            self.back_btn.setVisible(False)
            self.nav_label.setText(T("discovery.batch_resolve.search_results"))
        else:
            self.back_btn.setVisible(True)
            self.nav_label.setText(title or T("discovery.batch_resolve.searching")) # Or Browsing

        # Search Type from combo
        search_type = self.search_type_combo.currentData()
        year = self.year_input.value() if self.year_input.value() > 0 else None
        
        # Use S/E refinement if visible
        s_num = None
        e_num = None
        if self.tv_selector.isVisible():
            vals = self.tv_selector.get_values()
            s_num = vals['season'] if vals['season'] > 0 else None
            e_num = vals['episode'] if vals['episode'] > 0 else None
        
        # Season/Episode overrides for browsing mode
        browse_s = season_num
        browse_parent = parent_id

        # Search refinement filters from UI
        refine_s = s_num if mode == "search" else None
        refine_e = e_num if mode == "search" else None

        self.search_worker = SearchWorker(
            self.engine, query, year, search_type, mode, 
            parent_id=browse_parent, 
            season_num=browse_s or refine_s, 
            ep_num=refine_e
        )
        self.search_worker.results_found.connect(self._on_search_results)
        self.search_worker.finished.connect(self._on_worker_finished)
        self.search_worker.start()

    def _on_worker_finished(self):
        # If the list is still showing "Searching...", it means no results were found or an error occurred
        if self.results_list.count() > 0 and self.results_list.item(0).text() == T("discovery.batch_resolve.searching"):
            self.results_list.clear()
            self.results_list.addItem(T("manual_resolve.no_matches"))

    def _on_search_type_changed(self):
        stype = self.search_type_combo.currentData()
        self.tv_selector.setVisible(stype == 'tv')
        # Ensure the internal container of the selector is also shown correctly
        self.tv_selector.tv_container.setVisible(stype == 'tv')

    @Slot(list, str)
    def _on_search_results(self, results, mode):
        self.results_list.clear()
        
        if not results:
            if mode == "error":
                self.results_list.addItem(T("common.error"))
            else:
                self.results_list.addItem(T("manual_resolve.no_matches"))
            return
            
        for res in results:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 60))
            item.setData(Qt.UserRole, res)
            widget = ResultItemWidget(res)
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)

    def _on_selection_changed(self):
        items = self.results_list.selectedItems()
        if not items:
            self.action_btn.setEnabled(False)
            return
        
        res = items[0].data(Qt.UserRole)
        if not res: return
        self.selected_media = res
        
        mtype = res.get('media_type', 'movie')
        
        # 1. Update Action Button Text
        if mtype == 'movie':
            self.action_btn.setText(T("discovery.batch_resolve.identify_movie", title=res.get('title', '')))
        else:
            self.action_btn.setText(T("discovery.batch_resolve.link_series", title=res.get('name', '')))
            
        self.action_btn.setEnabled(True)
        
        # 2. Update TV options visibility (Strictly hide for movies/extras)
        is_tv = mtype in ('tv', 'season', 'episode')
        self.tv_options_card.setVisible(is_tv)
        
        # 3. Update Preview
        self._update_preview()
        
        if is_tv:
            # Refresh depth options based on selection
            self.tv_depth_combo.blockSignals(True)
            self.tv_depth_combo.clear()
            self.tv_depth_combo.addItem(T("discovery.batch_resolve.depth.series"), "series")
            self.tv_depth_combo.addItem(T("discovery.batch_resolve.depth.season"), "season")
            self.tv_depth_combo.addItem(T("discovery.batch_resolve.depth.sequential"), "sequential")
            
            if res['media_type'] == 'tv': self.tv_depth_combo.setCurrentIndex(0)
            elif res['media_type'] == 'season': self.tv_depth_combo.setCurrentIndex(1)
            elif res['media_type'] == 'episode': self.tv_depth_combo.setCurrentIndex(2)
            self.tv_depth_combo.blockSignals(False)
            
        self._update_action_text()

    def _update_action_text(self):
        if not self.selected_media: return
        res = self.selected_media
        mtype = res['media_type']
        depth = self.tv_depth_combo.currentData() if self.tv_options_card.isVisible() else None
        
        if mtype == 'movie': 
            self.action_btn.setText(T("discovery.batch_resolve.identify_movie", title=res['title']))
        elif depth == 'series':
            self.action_btn.setText(T("discovery.batch_resolve.link_series", title=res['title']))
        elif depth == 'season':
            s_num = self.tv_selector.get_values()['season']
            self.action_btn.setText(T("discovery.batch_resolve.link_season", number=s_num))
        elif depth == 'sequential':
            s_num = self.tv_selector.get_values()['season']
            e_start = self.tv_selector.get_values()['episode']
            self.action_btn.setText(T("discovery.batch_resolve.link_sequential", s=s_num, e=e_start))
        else:
            # Fallback
            self.action_btn.setText(T("discovery.batch_resolve.action_btn_default"))

        # Update Preview
        self.preview_title.setText(res['title'])
        meta = f"Type: {res['media_type'].capitalize()}"
        if res.get('year'): meta += f" • {res['year']}"
        self.preview_meta.setText(meta)
        self.preview_overview.setText(res.get('overview', ""))
        
        if res.get('poster_path'):
            self._load_poster(res['poster_path'])
        else:
            self.preview_poster.setText(T("discovery.batch_resolve.no_poster"))

    def _on_item_double_clicked(self, item):
        res = item.data(Qt.UserRole)
        if not res: return
        if res['media_type'] == 'tv':
            self.nav_stack.append(("search", None, None, T("discovery.batch_resolve.search_results")))
            self._on_search_clicked(mode="seasons", parent_id=res['tmdb_id'], title=res['title'])
            self.tv_selector.set_values(0, 0)
        elif res['media_type'] == 'season':
            self.nav_stack.append(("seasons", res['show_id'], None, self.nav_label.text()))
            self._on_search_clicked(mode="episodes", parent_id=res['show_id'], season_num=res['season_number'], title=res['title'])
            self.tv_selector.set_values(res['season_number'], 0)
        elif res['media_type'] == 'episode':
            self.tv_selector.set_values(res['season_number'], res['episode_number'])

    def _on_back(self):
        if not self.nav_stack: return
        mode, parent_id, season_num, title = self.nav_stack.pop()
        self._on_search_clicked(mode=mode, parent_id=parent_id, season_num=season_num, title=title)

    def _load_poster(self, poster_path):
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(base_dir, 'data', 'cache', 'posters')
        local_path = os.path.join(cache_dir, poster_path.lstrip('/'))
        if os.path.exists(local_path):
            self._on_poster_loaded(QPixmap(local_path))
            return
        url = f"https://image.tmdb.org/t/p/w200{poster_path}"
        self.poster_worker = ImageDownloader(url, local_path)
        self.poster_worker.finished.connect(self._on_poster_loaded)
        self.poster_worker.start()

    def _on_poster_loaded(self, pixmap):
        if not pixmap.isNull():
            scaled = pixmap.scaled(self.preview_poster.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_poster.setPixmap(scaled)

    def _on_apply(self):
        if not self.selected_media: return
        res = self.selected_media
        depth = self.tv_depth_combo.currentData() if self.tv_options_card.isVisible() else 'default'
        vals = self.tv_selector.get_values()
        
        # Prepare actual media result (Series level if it's episode/season)
        actual_res = res.copy()
        if res['media_type'] in ('episode', 'season'):
            actual_res['media_type'] = 'tv'
            actual_res['tmdb_id'] = res.get('show_id', res['tmdb_id'])
        
        # Store media item in DB
        mid = self.engine.resolver.library.store_result(actual_res)
        
        updates_list = []
        is_multipart = self.file_list.count() > 1
        current_ep = vals['episode']
        
        for i in range(self.file_list.count()):
            f = self.file_list.item(i).data(Qt.UserRole)
            updates = {'id': f['id']}
            
            # Base logic
            if res['media_type'] == 'movie':
                updates['fn_media_type'] = 'movie'
                updates['category'] = 'video'
                self.engine.resolver._finalize_match(f['id'], mid, actual_res, f, status='matched')
            
            elif depth == 'series':
                updates['fn_media_type'] = 'tv'
                updates['category'] = 'video'
                self.engine.db.media.link_file_to_media(f['id'], mid, None)
                updates['match_status'] = 'pending' 
                
            elif depth == 'season':
                updates['fn_media_type'] = 'tv'
                updates['fn_season'] = vals['season']
                updates['category'] = 'video'
                self.engine.db.media.link_file_to_media(f['id'], mid, None)
                updates['match_status'] = 'pending'
                
            elif depth == 'sequential':
                updates['fn_media_type'] = 'tv'
                updates['fn_season'] = vals['season']
                updates['fn_episode'] = str(current_ep)
                updates['category'] = 'video'
                
                # Link to specific episode
                self.engine.resolver._finalize_match(f['id'], mid, actual_res, updates, status='matched')
                current_ep += 1 # Increment for next file in batch
            
            updates_list.append(updates)
            
        # Final commit to DB
        try:
            for up in updates_list:
                self.engine.db.update_file(up['id'], **up)
            
            QMessageBox.information(self, T("common.success"), T("discovery.batch_resolve.success_msg", count=len(updates_list)))
            self.accept()
        except Exception as e:
            logger.error(f"BatchResolve Error: {e}")
            QMessageBox.critical(self, T("common.error"), str(e))
            QMessageBox.critical(self, T("common.error"), f"Failed: {e}")
