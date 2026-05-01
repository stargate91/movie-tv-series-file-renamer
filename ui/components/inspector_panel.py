from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QFrame, QScrollArea, QComboBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from ui.components.image_widgets import ImageLoader
import os

class InspectorPanel(QWidget):
    """
    Side panel for batch-resolving metadata and managing selections.
    """
    apply_metadata = Signal(list, dict) # [file_paths], metadata_details
    remove_requested = Signal(list)     # [file_paths]
    type_change_requested = Signal(list, str) # [file_paths], new_type
    season_change_requested = Signal(list, str) # [file_paths], season_num
    episode_change_requested = Signal(list, str) # [file_paths], episode_start
    sequence_requested = Signal() # Trigger order wizard

    def __init__(self, parent, pipeline):
        super().__init__(parent)
        self.pipeline = pipeline
        self.selected_paths = []
        self.search_results = []
        
        self.setFixedWidth(320)
        self.setObjectName("InspectorPanel")
        self.setStyleSheet("""
            #InspectorPanel {
                background-color: #f5f7fa;
                border-left: 1px solid #d6dce5;
            }
            QLabel { color: #1a1a2e; }
            QLabel#Title { font-size: 15px; font-weight: bold; color: #0066cc; }
            QLabel#SubTitle { color: #5a6a7a; font-size: 10px; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }
            
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #c8d1dc;
                border-radius: 4px;
                padding: 7px 10px;
                color: #1a1a2e;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
            }
            QLineEdit:focus { border-color: #0078d4; border-width: 2px; }
            QLineEdit::placeholder { color: #9aa5b4; }
            
            QPushButton#ActionBtn {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton#ActionBtn:hover { background-color: #106ebe; }
            QPushButton#ActionBtn:pressed { background-color: #005a9e; }
            QPushButton#ActionBtn:disabled { background-color: #c8d1dc; color: #9aa5b4; }

            QPushButton#SecondaryBtn {
                background-color: #ffffff;
                border: 1px solid #c8d1dc;
                color: #1a1a2e;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton#SecondaryBtn:hover { background-color: #e8edf2; border-color: #0078d4; }
            QPushButton#SecondaryBtn:pressed { background-color: #d6dce5; }
            
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #c8d1dc;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                border-bottom: 1px solid #e8edf2;
                padding: 5px;
                color: #1a1a2e;
            }
            QListWidget::item:selected {
                background-color: #e5f1fb;
                border-left: 3px solid #0078d4;
            }
            QListWidget::item:hover {
                background-color: #f0f4f8;
            }
            
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #c8d1dc;
                border-radius: 4px;
                padding: 5px 8px;
                color: #1a1a2e;
            }
            QComboBox:hover { border-color: #0078d4; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #c8d1dc;
                selection-background-color: #e5f1fb;
                selection-color: #1a1a2e;
            }
            
            QScrollArea { border: none; background: transparent; }
            
            QFrame[frameShape="4"] { background-color: #d6dce5; max-height: 1px; }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        self.init_ui()
        
        self.scroll.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll)

    def init_ui(self):
        title = QLabel("Selection Inspector")
        title.setObjectName("Title")
        self.layout.addWidget(title)
        
        self.count_lbl = QLabel("0 items selected")
        self.count_lbl.setObjectName("SubTitle")
        self.layout.addWidget(self.count_lbl)
        
        # --- Batch Actions ---
        actions_frame = QFrame()
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("SecondaryBtn")
        actions_layout.addWidget(self.clear_btn)
        
        self.remove_btn = QPushButton("🗑️ Remove")
        self.remove_btn.setObjectName("SecondaryBtn")
        self.remove_btn.setStyleSheet("color: #d13438; border-color: #d13438;")
        self.remove_btn.clicked.connect(self.on_remove_clicked)
        actions_layout.addWidget(self.remove_btn)
        
        self.layout.addWidget(actions_frame)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #30363d;")
        self.layout.addWidget(line)

        # --- Resolution Controls Container ---
        self.res_container = QWidget()
        res_layout = QVBoxLayout(self.res_container)
        res_layout.setContentsMargins(0, 0, 0, 0)
        res_layout.setSpacing(10)
        
        res_layout.addWidget(QLabel("BATCH RESOLVE", objectName="SubTitle"))
        
        # Type Toggle
        res_layout.addWidget(QLabel("TYPE", objectName="SubTitle"))
        type_box = QWidget()
        t_layout = QHBoxLayout(type_box)
        t_layout.setContentsMargins(0,0,0,0)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Movie", "TV Show"])
        t_layout.addWidget(self.type_combo, 1)
        
        self.set_type_btn = QPushButton("Set Type")
        self.set_type_btn.setObjectName("SecondaryBtn")
        self.set_type_btn.clicked.connect(self.on_set_type_clicked)
        t_layout.addWidget(self.set_type_btn)
        res_layout.addWidget(type_box)
        
        # Search Box
        res_layout.addWidget(QLabel("SEARCH & MATCH", objectName="SubTitle"))
        search_box = QWidget()
        s_layout = QHBoxLayout(search_box)
        s_layout.setContentsMargins(0,0,0,0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for title...")
        self.search_input.returnPressed.connect(self.perform_search)
        s_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍")
        self.search_btn.setFixedSize(35, 35)
        self.search_btn.setObjectName("SecondaryBtn")
        self.search_btn.clicked.connect(self.perform_search)
        s_layout.addWidget(self.search_btn)
        res_layout.addWidget(search_box)
        
        # Season & Episode Override
        self.tv_overrides_frame = QWidget()
        tv_layout = QVBoxLayout(self.tv_overrides_frame)
        tv_layout.setContentsMargins(0, 0, 0, 0)
        
        s_box = QWidget()
        s_lay = QHBoxLayout(s_box)
        s_lay.setContentsMargins(0, 0, 0, 0)
        self.season_input = QLineEdit()
        self.season_input.setPlaceholderText("Season Override")
        self.set_season_btn = QPushButton("Set")
        self.set_season_btn.setObjectName("SecondaryBtn")
        self.set_season_btn.clicked.connect(self.on_set_season_clicked)
        s_lay.addWidget(self.season_input, 1)
        s_lay.addWidget(self.set_season_btn)
        tv_layout.addWidget(s_box)
        
        self.e_box = QWidget()
        e_lay = QHBoxLayout(self.e_box)
        e_lay.setContentsMargins(0, 0, 0, 0)
        self.episode_input = QLineEdit()
        self.episode_input.setPlaceholderText("Episode Override")
        self.set_episode_btn = QPushButton("Set")
        self.set_episode_btn.setObjectName("SecondaryBtn")
        self.set_episode_btn.clicked.connect(self.on_set_episode_clicked)
        e_lay.addWidget(self.episode_input, 1)
        e_lay.addWidget(self.set_episode_btn)
        tv_layout.addWidget(self.e_box)
        
        self.sequence_btn = QPushButton("🪄 Sequence Episodes Wizard")
        self.sequence_btn.setObjectName("PrimaryBtn")
        self.sequence_btn.clicked.connect(self.sequence_requested.emit)
        self.sequence_btn.setVisible(False)
        tv_layout.addWidget(self.sequence_btn)
        
        res_layout.addWidget(self.tv_overrides_frame)
        self.type_combo.currentTextChanged.connect(lambda t: self.tv_overrides_frame.setVisible(t == "TV Show"))
        self.tv_overrides_frame.setVisible(False)
        
        res_layout.addWidget(QLabel("RESULTS", objectName="SubTitle"))
        self.results_list = QListWidget()
        self.results_list.setFixedHeight(280)
        res_layout.addWidget(self.results_list)
        
        self.apply_btn = QPushButton("✅ Apply to Selection")
        self.apply_btn.setObjectName("ActionBtn")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.on_apply_clicked)
        res_layout.addWidget(self.apply_btn)
        
        self.layout.addWidget(self.res_container)
        self.layout.addStretch()
        
        self.results_list.itemSelectionChanged.connect(lambda: self.apply_btn.setEnabled(True))
        
    def set_minimal_mode(self, minimal):
        self.res_container.setVisible(not minimal)
        
    def on_remove_clicked(self):
        if self.selected_paths:
            self.remove_requested.emit(self.selected_paths)

    def update_selection(self, paths):
        self.selected_paths = paths
        count = len(paths)
        self.count_lbl.setText(f"{count} items selected")
        self.setVisible(count > 0)
        
        if count > 0:
            first_meta = self.pipeline.metadata_map.get(paths[0], {})
            if not isinstance(first_meta, dict): first_meta = {}
            guessed_title = first_meta.get('extras', {}).get('title', '')
            if guessed_title and not self.search_input.text():
                self.search_input.setText(guessed_title)
            
            f_type = first_meta.get('file_type', 'movie')
            self.type_combo.setCurrentText("Movie" if f_type == 'movie' else "TV Show")
            
            # Toggle Single vs Bulk Episode inputs
            if count > 1:
                self.e_box.setVisible(False)
                self.sequence_btn.setVisible(True)
            else:
                self.e_box.setVisible(True)
                self.sequence_btn.setVisible(False)
            
            # Auto-search on selection if results are empty
            if guessed_title and self.results_list.count() == 0:
                self.perform_search()

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query: return
        
        self.search_btn.setText("⏳")
        self.search_btn.setEnabled(False)
        
        search_type = self.type_combo.currentText()
        try:
            if search_type == "Movie":
                res = self.pipeline.api.get_from_tmdb_movie(query, None)
            else:
                res = self.pipeline.api.get_from_tmdb_tv(query, None)
            
            self.display_results(res.get('results', []) if res else [])
        except Exception as e:
            self.results_list.clear()
            self.results_list.addItem(f"Error: {e}")
        finally:
            self.search_btn.setText("🔍")
            self.search_btn.setEnabled(True)

    def display_results(self, results):
        self.results_list.clear()
        self.search_results = results
        
        for res in results:
            title = res.get('title') or res.get('name', 'Unknown')
            date = res.get('release_date') or res.get('first_air_date', '')
            year = f"({date[:4]})" if date else ""
            
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 5, 5, 5)
            
            p_path = res.get('poster_path')
            url = f"https://image.tmdb.org/t/p/w92{p_path}" if p_path else None
            poster = ImageLoader(url, 30, 45)
            item_layout.addWidget(poster)
            
            lbl = QLabel(f"<b>{title}</b> {year}")
            lbl.setStyleSheet("font-size: 11px; color: #1a1a2e;")
            lbl.setWordWrap(True)
            item_layout.addWidget(lbl, 1)
            
            list_item = QListWidgetItem(self.results_list)
            list_item.setData(Qt.UserRole, res)
            list_item.setSizeHint(item_widget.sizeHint())
            self.results_list.addItem(list_item)
            self.results_list.setItemWidget(list_item, item_widget)

    def on_set_type_clicked(self):
        new_type = 'episode' if self.type_combo.currentText() == 'TV Show' else 'movie'
        self.type_change_requested.emit(self.selected_paths, new_type)

    def on_set_season_clicked(self):
        val = self.season_input.text().strip()
        if val:
            self.season_change_requested.emit(self.selected_paths, val)
            self.season_input.clear()

    def on_set_episode_clicked(self):
        val = self.episode_input.text().strip()
        if val:
            self.episode_change_requested.emit(self.selected_paths, val)
            self.episode_input.clear()

    def on_apply_clicked(self):
        curr = self.results_list.currentItem()
        if not curr: return
        
        selected_meta = curr.data(Qt.UserRole)
        # Add season override if provided
        season_override = self.season_input.text().strip()
        if season_override:
            selected_meta['season_override'] = season_override
        
        # Add episode start override if provided
        episode_override = self.episode_input.text().strip()
        if episode_override:
            selected_meta['episode_override'] = episode_override
            
        self.apply_metadata.emit(self.selected_paths, selected_meta)
        self.results_list.clear()
        self.search_input.clear()
        self.season_input.clear()
        self.episode_input.clear()
        self.apply_btn.setEnabled(False)
