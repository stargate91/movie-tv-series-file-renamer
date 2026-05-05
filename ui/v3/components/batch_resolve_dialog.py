import logging
from PySide6.QtCore import Qt, QSize, Signal, Slot
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QWidget,
                             QPushButton, QListWidget, QListWidgetItem, QLabel, QFrame, 
                             QScrollArea, QSpinBox, QMessageBox, QAbstractItemView)
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
        lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(lbl)
        
        self.file_list = QListWidget()
        self.file_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.file_list.setDefaultDropAction(Qt.MoveAction)
        self.file_list.setStyleSheet(Theme.get_sidebar_list_style())
        left_layout.addWidget(self.file_list)
        
        hint = QLabel(T("discovery.batch_resolve.drag_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-size: 11px;")
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
        self.nav_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Theme.TEXT_MAIN};")
        
        nav_box.addWidget(self.back_btn)
        nav_box.addWidget(self.nav_label)
        nav_box.addStretch()
        right_pane.addLayout(nav_box)
        
        # Search Tools
        search_box = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("discovery.batch_resolve.search_placeholder"))
        self.search_input.setFixedHeight(40)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        
        self.search_btn = QPushButton(T("discovery.batch_resolve.search_btn"))
        self.search_btn.setFixedHeight(40)
        self.search_btn.setFixedWidth(100)
        self.search_btn.clicked.connect(self._on_search_clicked)
        
        search_box.addWidget(self.search_input)
        search_box.addWidget(self.search_btn)
        right_pane.addLayout(search_box)

        # Results & Preview Area
        content_row = QHBoxLayout()
        
        self.results_list = QListWidget()
        self.results_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        content_row.addWidget(self.results_list, 3)
        
        self.preview_panel = self._create_preview_panel()
        content_row.addWidget(self.preview_panel, 2)
        
        right_pane.addLayout(content_row)
        
        # Footer Action
        self.action_btn = QPushButton(T("discovery.batch_resolve.action_btn_default"))
        self.action_btn.setFixedHeight(50)
        self.action_btn.setEnabled(False)
        self.action_btn.setStyleSheet(Theme.get_primary_button_style())
        self.action_btn.clicked.connect(self._on_apply)
        right_pane.addWidget(self.action_btn)
        
        self.main_layout.addLayout(right_pane)

    def _create_preview_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border: 1px solid {Theme.BORDER}; border-radius: 12px;")
        layout = QVBoxLayout(panel)
        
        self.preview_poster = QLabel(T("discovery.batch_resolve.no_selection"))
        self.preview_poster.setAlignment(Qt.AlignCenter)
        self.preview_poster.setFixedSize(200, 300)
        self.preview_poster.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 8px;")
        
        self.preview_title = QLabel(T("discovery.batch_resolve.select_result"))
        self.preview_title.setWordWrap(True)
        self.preview_title.setStyleSheet(f"font-weight: 800; font-size: 15px; color: {Theme.TEXT_MAIN};")
        
        self.preview_meta = QLabel("")
        self.preview_meta.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: 700;")
        
        self.preview_overview = QLabel("")
        self.preview_overview.setWordWrap(True)
        self.preview_overview.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")
        
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

        # We always search for both for batch
        self.search_worker = SearchWorker(self.engine, query, None, 'both', mode, parent_id, season_num)
        self.search_worker.results_found.connect(self._on_search_results)
        self.search_worker.start()

    @Slot(list, str)
    def _on_search_results(self, results, mode):
        self.results_list.clear()
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
        self.action_btn.setEnabled(True)
        
        # Update Action Text
        mtype = res['media_type']
        if mtype == 'movie': 
            self.action_btn.setText(T("discovery.batch_resolve.identify_movie", title=res['title']))
        elif mtype == 'tv': 
            self.action_btn.setText(T("discovery.batch_resolve.link_series", title=res['title']))
        elif mtype == 'season': 
            self.action_btn.setText(T("discovery.batch_resolve.link_season", number=res['season_number']))
        elif mtype == 'episode': 
            self.action_btn.setText(T("discovery.batch_resolve.identify_episode", s=res['season_number'], e=res['episode_number']))

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
            self.nav_stack.append(("search", None, None, "Search Results"))
            self._on_search_clicked(mode="seasons", parent_id=res['tmdb_id'], title=res['title'])
        elif res['media_type'] == 'season':
            self.nav_stack.append(("seasons", res['show_id'], None, self.nav_label.text()))
            self._on_search_clicked(mode="episodes", parent_id=res['show_id'], season_num=res['season_number'], title=res['title'])

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
        
        # Prepare actual media result (Series level if it's episode/season)
        actual_res = res.copy()
        if res['media_type'] in ('episode', 'season'):
            actual_res['media_type'] = 'tv'
            actual_res['tmdb_id'] = res.get('show_id', res['tmdb_id'])
        
        # Store media item in DB
        mid = self.engine.resolver.library.store_result(actual_res)
        
        updates_list = []
        is_multipart = self.file_list.count() > 1
        
        for i in range(self.file_list.count()):
            f = self.file_list.item(i).data(Qt.UserRole)
            updates = {'id': f['id']}
            
            # Base logic
            if res['media_type'] == 'movie':
                # Link to Movie. We DON'T auto-assign parts here to allow for Edition conflicts.
                updates['fn_media_type'] = 'movie'
                updates['category'] = 'video'
                self.engine.resolver._finalize_match(f['id'], mid, actual_res, f, status='matched')
            
            elif res['media_type'] == 'tv':
                # Partial Match (Series only)
                updates['fn_media_type'] = 'tv'
                updates['category'] = 'video'
                # Just link to series, no episode ID yet
                self.engine.db.media.link_file_to_media(f['id'], mid, None)
                updates['match_status'] = 'pending' # Stays in review
                
            elif res['media_type'] == 'season':
                # Partial Match (Series + Season)
                updates['fn_media_type'] = 'tv'
                updates['fn_season'] = res['season_number']
                updates['category'] = 'video'
                self.engine.db.media.link_file_to_media(f['id'], mid, None)
                updates['match_status'] = 'pending'
                
            elif res['media_type'] == 'episode':
                # Full Match (Multiple files for 1 episode -> Parts)
                updates['fn_media_type'] = 'tv'
                updates['fn_season'] = res['season_number']
                updates['fn_episode'] = str(res['episode_number'])
                updates['category'] = 'video'
                if is_multipart: updates['part_number'] = i + 1
                
                # Use _finalize_match which handles linking to the specific episode
                self.engine.resolver._finalize_match(f['id'], mid, actual_res, f, status='matched')

            updates_list.append(updates)

        try:
            self.engine.db.files.bulk_update_files(updates_list)
            QMessageBox.information(self, T("common.success"), T("discovery.batch_resolve.success_msg", count=len(updates_list)))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, T("common.error"), f"Failed: {e}")
