import logging
import json
from PySide6.QtCore import Qt, QSize, Signal, Slot
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QWidget,
                             QPushButton, QListWidget, QListWidgetItem, QLabel, QFrame, 
                             QScrollArea, QSpinBox, QMessageBox)
from PySide6.QtGui import QPixmap

from ui.v3.styles.theme import Theme
from ui.v3.components.image_loader import ImageDownloader
from .manual_resolve.searcher import SearchWorker
from .manual_resolve.tv_selector import TVMetadataSelector
from .manual_resolve.result_widget import ResultItemWidget
from core.i18n import T

logger = logging.getLogger(__name__)

class ManualResolveDialog(QDialog):
    """
    Orchestrator for manual media identification.
    Decomposed into Searcher (Logic), TVMetadataSelector (UI), and ResultItemWidget (UI).
    """
    def __init__(self, engine, file_data, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.file_id = file_data['id']
        self.file_name = file_data['file_name']
        self.selected_media = None
        self.basket = []
        self.search_worker = None
        self.nav_stack = [] # History of (mode, parent_id, season_num, title)
        self.multi_match_mode = False

        self.setWindowTitle(f"Manual Resolve: {self.file_name}")
        self.setMinimumSize(850, 750)
        self.setStyleSheet(Theme.get_main_stylesheet())
        
        self._init_ui()
        self._prefill_from_data(file_data)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setSpacing(15)

        # 1. Header Bar
        header = QHBoxLayout()
        self.back_btn = QPushButton(f"← {T('manual_resolve.back')}")
        self.back_btn.setObjectName("SecondaryButton")
        self.back_btn.setFixedWidth(80)
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._on_back)
        
        self.nav_label = QLabel(T("manual_resolve.search_results"))
        self.nav_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Theme.TEXT_MAIN};")
        
        self.mode_btn = QPushButton(T("manual_resolve.link_multiple"))
        self.mode_btn.setObjectName("SecondaryButton")
        self.mode_btn.setFixedWidth(160)
        self.mode_btn.setCheckable(True)
        self.mode_btn.clicked.connect(self._toggle_multi_match)

        header.addWidget(self.back_btn)
        header.addWidget(self.nav_label)
        header.addStretch()
        header.addWidget(self.mode_btn)
        layout.addLayout(header)
        layout.addWidget(Theme.create_hline())

        # 2. Search Tools
        tools = QVBoxLayout()
        tools.setSpacing(10)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("manual_resolve.search_placeholder"))
        self.search_input.setFixedHeight(40)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        
        self.search_btn = QPushButton(T("manual_resolve.search_btn"))
        self.search_btn.setFixedHeight(40)
        self.search_btn.setFixedWidth(100)
        self.search_btn.clicked.connect(self._on_search_clicked)
        
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_btn)
        tools.addLayout(search_row)

        filters_row = QHBoxLayout()
        self.year_spin = QSpinBox()
        self.year_spin.setRange(0, 2100)
        self.year_spin.setSpecialValueText(T("manual_resolve.any_year"))
        self.year_spin.setFixedWidth(100)
        
        filters_row.addWidget(QLabel(T("manual_resolve.year_label")))
        filters_row.addWidget(self.year_spin)
        filters_row.addSpacing(20)

        self.tv_selector = TVMetadataSelector()
        filters_row.addWidget(self.tv_selector)
        tools.addLayout(filters_row)
        layout.addLayout(tools)

        # 3. Content Area
        self.content_row = QHBoxLayout()
        self.content_row.setSpacing(20)
        
        # Results List
        res_col = QVBoxLayout()
        self.results_list = QListWidget()
        self.results_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        res_col.addWidget(self.results_list)
        
        self.action_btn = QPushButton(T("manual_resolve.match_btn"))
        self.action_btn.setFixedHeight(45)
        self.action_btn.setEnabled(False)
        self.action_btn.setStyleSheet(Theme.get_primary_button_style())
        self.action_btn.clicked.connect(self._on_action_clicked)
        res_col.addWidget(self.action_btn)
        self.content_row.addLayout(res_col, 2)
        
        # Preview Panel
        self.preview_panel = self._create_preview_panel()
        self.content_row.addWidget(self.preview_panel)
        
        # Basket (Hidden by default)
        self.basket_widget = self._create_basket_widget()
        self.content_row.addWidget(self.basket_widget, 2)
        
        layout.addLayout(self.content_row)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(QPushButton(T("common.cancel"), clicked=self.reject, objectName="SecondaryButton", fixedWidth=100, fixedHeight=40))
        layout.addLayout(footer)

    def _create_preview_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border: 1px solid {Theme.BORDER}; border-radius: 12px;")
        panel.setFixedWidth(280)
        layout = QVBoxLayout(panel)
        
        self.preview_poster = QLabel(T("manual_resolve.no_selection"))
        self.preview_poster.setAlignment(Qt.AlignCenter)
        self.preview_poster.setFixedSize(250, 375)
        self.preview_poster.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 8px;")
        
        self.preview_title = QLabel(T("manual_resolve.select_result"))
        self.preview_title.setWordWrap(True)
        self.preview_title.setStyleSheet(f"font-weight: 800; font-size: 16px; color: {Theme.TEXT_MAIN};")
        
        self.preview_meta = QLabel("")
        self.preview_meta.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: 700;")
        
        self.preview_overview = QLabel("")
        self.preview_overview.setWordWrap(True)
        self.preview_overview.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 12px;")
        
        layout.addWidget(self.preview_poster, 0, Qt.AlignCenter)
        layout.addWidget(self.preview_title)
        layout.addWidget(self.preview_meta)
        layout.addWidget(self.preview_overview)
        layout.addStretch()
        return panel

    def _create_basket_widget(self):
        widget = QWidget()
        widget.setVisible(False)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header = QHBoxLayout()
        header.addWidget(QLabel(T("manual_resolve.basket")))
        clear_btn = QPushButton(T("manual_resolve.clear"), clicked=self._clear_basket, objectName="SecondaryButton")
        header.addWidget(clear_btn)
        layout.addLayout(header)
        
        self.basket_list = QListWidget()
        layout.addWidget(self.basket_list)
        
        self.confirm_btn = QPushButton(T("manual_resolve.confirm_all"), clicked=self._on_confirm)
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setFixedHeight(45)
        self.confirm_btn.setStyleSheet(Theme.get_success_button_style())
        layout.addWidget(self.confirm_btn)
        return widget

    def _prefill_from_data(self, data):
        self.search_input.setText(data.get('fn_title') or data.get('fd_title') or "")
        self.year_spin.setValue(int(data.get('fn_year') or 0))
        
        self.tv_selector.set_values(
            data.get('fn_media_type') or data.get('fd_media_type') or 'movie',
            data.get('fn_season') or data.get('fd_season') or 0,
            data.get('fn_episode') or data.get('fd_episode') or 0
        )

        # Auto-search or show candidates
        candidates = self.engine.db.get_candidates(self.file_id)
        if candidates:
            self._on_search_results(candidates, "candidates")
        elif self.search_input.text():
            self._on_search_clicked()

    def _on_search_clicked(self, mode="search", parent_id=None, season_num=None, title=None):
        query = self.search_input.text().strip()
        if not query and mode == "search": return

        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.results_found.disconnect()
            self.search_worker.terminate()

        self.results_list.clear()
        self.results_list.addItem("Searching API...")
        self.action_btn.setEnabled(False)
        
        if mode == "search":
            self.nav_stack = []
            self.back_btn.setVisible(False)
            self.nav_label.setText("Search Results")
        else:
            self.back_btn.setVisible(True)
            self.nav_label.setText(title or "Browsing...")

        vals = self.tv_selector.get_values()
        year = self.year_spin.value()
        year_param = str(year) if year > 0 else None

        self.search_worker = SearchWorker(self.engine, query, year_param, vals['type'], mode, parent_id, season_num)
        self.search_worker.results_found.connect(self._on_search_results)
        self.search_worker.start()

    @Slot(list, str)
    def _on_search_results(self, results, mode):
        self.results_list.clear()
        if mode == "candidates": self.nav_label.setText(T("manual_resolve.candidates_found", count=len(results)))
        
        for res in results:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 60))
            item.setData(Qt.UserRole, res)
            
            widget = ResultItemWidget(res)
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)
            
        if not results:
            self.results_list.addItem(T("manual_resolve.no_matches"))

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
        meta = T("manual_resolve.type_label", type=res['media_type'].capitalize())
        if res.get('year'): meta += f" • {res['year']}"
        self.preview_meta.setText(meta)
        self.preview_overview.setText(res.get('overview', ""))
        
        if res.get('poster_path'):
            self._load_poster(res['poster_path'])
        else:
            self.preview_poster.setText(T("manual_resolve.no_poster"))

    def _on_item_double_clicked(self, item):
        res = item.data(Qt.UserRole)
        if not res: return
        
        if res['media_type'] == 'tv':
            self.nav_stack.append(("search", None, None, T("manual_resolve.search_results")))
            self._on_search_clicked(mode="seasons", parent_id=res['tmdb_id'], title=res['title'])
        elif res['media_type'] == 'season':
            self.nav_stack.append(("seasons", res['show_id'], None, self.nav_label.text()))
            self._on_search_clicked(mode="episodes", parent_id=res['show_id'], season_num=res['season_number'], title=res['title'])
        else:
            self._on_action_clicked()

    def _on_back(self):
        if not self.nav_stack: return
        mode, parent_id, season_num, title = self.nav_stack.pop()
        self._on_search_clicked(mode=mode, parent_id=parent_id, season_num=season_num, title=title)

    def _toggle_multi_match(self, checked):
        self.multi_match_mode = checked
        self.basket_widget.setVisible(checked)
        if checked:
            self.setMinimumWidth(1150)
            self.action_btn.setText(T("manual_resolve.add_basket"))
        else:
            self.setMinimumWidth(850)
            self.action_btn.setText(T("manual_resolve.match_btn"))

    def _on_action_clicked(self):
        if not self.selected_media: return
        vals = self.tv_selector.get_values()
        
        m = self.selected_media
        s = m.get('season_number', vals['season'])
        e = m.get('episode_number', vals['episode'])
        
        if self.multi_match_mode:
            self.basket.append({'media': m, 's': s, 'e': e})
            self._refresh_basket_ui()
        else:
            self.basket = [{'media': m, 's': s, 'e': e}]
            self._on_confirm()

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
        self.confirm_btn.setEnabled(len(self.basket) > 0)

    def _on_confirm(self):
        if not self.basket: return
        self.engine.db.files.clear_match(self.file_id)
        
        all_episodes = []
        last_s, last_type = None, None
        
        for item in self.basket:
            res = item['media']
            actual_res = res.copy()
            if res['media_type'] in ('episode', 'season'):
                actual_res['media_type'] = 'tv'
                actual_res['tmdb_id'] = res.get('show_id', res['tmdb_id'])

            s_num, e_num = item['s'], item['e']
            last_s, last_type = s_num, actual_res['media_type']
            all_episodes.append(e_num)
            
            # Finalize using resolver
            mid = self.engine.resolver.library.store_result(actual_res)
            vid_mock = self.engine.db.files.get_file_by_id(self.file_id)
            vid_mock['fn_season'], vid_mock['fn_episode'], vid_mock['fn_media_type'] = s_num, str(e_num), actual_res['media_type']
            self.engine.resolver._finalize_match(self.file_id, mid, actual_res, vid_mock, status='matched')
            
        # Update final file tags for multi-episode support
        if all_episodes:
            ep_val = str(all_episodes[0]) if len(all_episodes) == 1 else str(sorted(list(set(all_episodes))))
            self.engine.db.files.update_file(self.file_id, fn_season=last_s, fn_episode=ep_val, fn_media_type=last_type)
        self.accept()

    def _load_poster(self, poster_path):
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(base_dir, 'data', 'cache', 'posters')
        local_path = os.path.join(cache_dir, poster_path.lstrip('/'))

        if os.path.exists(local_path):
            self._on_poster_loaded(QPixmap(local_path))
            return

        url = f"https://image.tmdb.org/t/p/w200{poster_path}"
        self.preview_poster.setText("Loading...")
        self.poster_worker = ImageDownloader(url, local_path)
        self.poster_worker.finished.connect(self._on_poster_loaded)
        self.poster_worker.start()

    def _on_poster_loaded(self, pixmap):
        if not pixmap.isNull():
            scaled = pixmap.scaled(self.preview_poster.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_poster.setPixmap(scaled)
        else:
            self.preview_poster.setText(T("manual_resolve.no_poster"))
