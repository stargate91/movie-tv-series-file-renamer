import os
import sys
import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem,
                             QScrollArea, QWidget, QCheckBox, QComboBox, 
                             QSpinBox, QFrame, QAbstractItemView, QMessageBox, QLineEdit)
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from core.engine.metadata_rules import MetadataRules

logger = logging.getLogger(__name__)

class BatchOperationsDialog(QDialog):
    """
    Dialog for performing bulk operations on multiple files.
    Features a reorderable list and checkbox-based property overrides.
    """
    def __init__(self, parent, engine, selected_files):
        super().__init__(parent)
        self.engine = engine
        self.selected_files = selected_files
        
        # Detect if we should use unified classification (all video/extra)
        self.is_video_batch = all(f.get('category') in ['video', 'extra'] for f in self.selected_files)
        
        self.setWindowTitle(f"Batch Operations ({len(self.selected_files)} files)")
        self.setMinimumSize(1000, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.setStyleSheet(Theme.get_main_stylesheet())
        
        self._init_ui()
        self._populate_list()
        self._populate_parents()

    def _init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # LEFT PANE: Sorter List
        self.left_pane_widget = QWidget()
        left_layout = QVBoxLayout(self.left_pane_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("1. File Selection / Order:", styleSheet="font-weight: bold; font-size: 14px;"))
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setStyleSheet(Theme.get_sidebar_list_style())
        left_layout.addWidget(self.list_widget)
        self.main_layout.addWidget(self.left_pane_widget, 1)

        # RIGHT PANE: Operations
        right_pane = QVBoxLayout()
        right_pane.addWidget(QLabel("2. Configure Properties:", styleSheet="font-weight: bold; font-size: 14px;"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)

        # --- Card 1: Category & Type ---
        self.cat_card = self._create_card("📁 Category & Type Override")
        
        self.chk_category = QCheckBox("Override main category:")
        self.combo_category = QComboBox()
        self.combo_category.addItems(["Video / Movie", "Extra / Bonus", "Subtitle", "Audio", "Image", "NFO / Meta"])
        self.combo_category.setEnabled(False)
        self.chk_category.toggled.connect(self.combo_category.setEnabled)
        self.combo_category.currentIndexChanged.connect(self._update_ui_visibility)
        
        # Unified Classification
        self.combo_classification = QComboBox()
        self.combo_classification.addItems(["Movie", "Episode", "Bonus Video"])
        self.combo_classification.currentIndexChanged.connect(self._on_classification_changed)
        self.combo_classification.setEnabled(False)
        self.chk_category.toggled.connect(self.combo_classification.setEnabled)

        self.chk_sub_category = QCheckBox("Override Sub-type:")
        self.combo_sub_category = QComboBox()
        self.combo_sub_category.setEditable(True)
        self.combo_sub_category.addItems(MetadataRules.get_sub_type_config('default')['items'])
        self.combo_sub_category.setEnabled(False)
        self.chk_sub_category.toggled.connect(self.combo_sub_category.setEnabled)
        
        self.chk_media_type = QCheckBox("Media Type (Videos only):")
        self.combo_media_type = QComboBox()
        self.combo_media_type.addItems(["Movie", "TV Series"])
        self.combo_media_type.setEnabled(False)
        self.chk_media_type.toggled.connect(self.combo_media_type.setEnabled)
        self.combo_media_type.currentIndexChanged.connect(self._update_ui_visibility)

        self.cat_card.layout().addWidget(self.chk_category)
        self.cat_card.layout().addWidget(self.combo_category)
        self.cat_card.layout().addWidget(self.combo_classification)
        self.cat_card.layout().addWidget(self.chk_sub_category)
        self.cat_card.layout().addWidget(self.combo_sub_category)
        self.cat_card.layout().addWidget(self.chk_media_type)
        self.cat_card.layout().addWidget(self.combo_media_type)
        scroll_layout.addWidget(self.cat_card)

        if self.is_video_batch:
            self.combo_category.hide()
            self.combo_media_type.hide()
            self.chk_media_type.hide()
        else:
            self.combo_classification.hide()

        # --- Card 2: TV Series ---
        self.tv_card = self._create_card("📺 TV Series & Episodes")
        self.chk_season = QCheckBox("Set Season for all:")
        self.spin_season = QSpinBox()
        self.spin_season.setRange(0, 999)
        self.spin_season.setEnabled(False)
        self.chk_season.toggled.connect(self.spin_season.setEnabled)
        
        self.chk_episodes = QCheckBox("Renumber Episodes (Top to Bottom)")
        ep_layout = QHBoxLayout()
        ep_layout.addWidget(QLabel("Start Episode:"))
        self.spin_episode_start = QSpinBox()
        self.spin_episode_start.setRange(0, 9999)
        self.spin_episode_start.setValue(1)
        self.spin_episode_start.setEnabled(False)
        ep_layout.addWidget(self.spin_episode_start)
        ep_layout.addStretch()
        self.chk_episodes.toggled.connect(self.spin_episode_start.setEnabled)
        
        self.tv_card.layout().addWidget(self.chk_season)
        self.tv_card.layout().addWidget(self.spin_season)
        self.tv_card.layout().addWidget(self.chk_episodes)
        self.tv_card.layout().addLayout(ep_layout)
        scroll_layout.addWidget(self.tv_card)

        # --- Card 3: Parts ---
        self.part_card = self._create_card("✂️ Multi-part files")
        self.chk_parts = QCheckBox("Renumber as Parts (CD1, CD2...)")
        p_layout = QHBoxLayout()
        self.combo_part_type = QComboBox()
        self.combo_part_type.addItems(["Part", "CD", "Disk"])
        self.combo_part_type.setEnabled(False)
        self.spin_part_start = QSpinBox()
        self.spin_part_start.setRange(1, 99)
        self.spin_part_start.setEnabled(False)
        p_layout.addWidget(self.combo_part_type)
        p_layout.addWidget(self.spin_part_start)
        self.chk_parts.toggled.connect(self.combo_part_type.setEnabled)
        self.chk_parts.toggled.connect(self.spin_part_start.setEnabled)
        
        self.part_card.layout().addWidget(self.chk_parts)
        self.part_card.layout().addLayout(p_layout)
        scroll_layout.addWidget(self.part_card)

        # --- Card 4: Tags & Linking ---
        self.meta_card = self._create_card("🏷️ Tags & Linking")
        self.chk_edition = QCheckBox("Set Edition:")
        self.lbl_edition = QLabel("Edition:") # Backing for edit_dialog similarity
        self.combo_edition = QComboBox()
        self.combo_edition.setEditable(True)
        self.combo_edition.addItems(["", "Theatrical", "Director's Cut", "Extended"])
        self.combo_edition.setEnabled(False)
        self.chk_edition.toggled.connect(self.combo_edition.setEnabled)

        self.chk_lang = QCheckBox("Override Language:")
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["ENG", "HUN", "GER", "FRA", "SPA"])
        self.combo_lang.setEnabled(False)
        self.chk_lang.toggled.connect(self.combo_lang.setEnabled)

        self.chk_parent = QCheckBox("Link to Parent:")
        self.combo_parent = QComboBox()
        self.combo_parent.setEnabled(False)
        self.chk_parent.toggled.connect(self.combo_parent.setEnabled)

        self.meta_card.layout().addWidget(self.chk_edition)
        self.meta_card.layout().addWidget(self.combo_edition)
        self.meta_card.layout().addWidget(self.chk_lang)
        self.meta_card.layout().addWidget(self.combo_lang)
        self.meta_card.layout().addWidget(self.chk_parent)
        self.meta_card.layout().addWidget(self.combo_parent)
        scroll_layout.addWidget(self.meta_card)

        scroll.setWidget(scroll_content)
        right_pane.addWidget(scroll)

        # Buttons
        btns = QHBoxLayout()
        btn_apply = QPushButton("Apply to Selected")
        btn_apply.setMinimumHeight(40)
        btn_apply.setStyleSheet(Theme.get_primary_button_style())
        btn_apply.clicked.connect(self._apply_changes)
        btns.addWidget(btn_apply)
        right_pane.addLayout(btns)

        self.main_layout.addLayout(right_pane, 2)
        self._load_initial_data()
        self._update_ui_visibility()

    def _load_initial_data(self):
        if not self.selected_files: return
        f = self.selected_files[0]
        cat = f.get('category', 'video')
        
        # Category
        self.combo_category.setCurrentText(MetadataRules.get_category_label(cat))
        if self.is_video_batch:
            if cat == 'extra': self.combo_classification.setCurrentText("Bonus Video")
            elif f.get('fn_media_type') == 'tv': self.combo_classification.setCurrentText("Episode")
            else: self.combo_classification.setCurrentText("Movie")

        # Sub-type
        self.combo_sub_category.setCurrentText(f.get('sub_category') or "")
        
        # TV/Movie
        self.spin_season.setValue(f.get('fn_season') or 0)
        self.combo_edition.setCurrentText(f.get('edition') or "")
        self.combo_lang.setCurrentText(f.get('language') or "ENG")
        
        # Parent
        parent_id = f.get('parent_file_id')
        if parent_id:
            # We'll set this after parents are populated
            self._initial_parent_id = parent_id

    def _on_classification_changed(self):
        cls = self.combo_classification.currentText()
        if cls == "Movie":
            self.combo_category.setCurrentText("Video / Movie")
            self.combo_media_type.setCurrentText("Movie")
        elif cls == "Episode":
            self.combo_category.setCurrentText("Video / Movie")
            self.combo_media_type.setCurrentText("TV Series")
        elif cls == "Bonus Video":
            self.combo_category.setCurrentText("Extra / Bonus")
        self._update_ui_visibility()

    def _create_card(self, title):
        card = QFrame()
        card.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 8px; border: 1px solid {Theme.BORDER};")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: bold; color: #E2E8F0; border: none;")
        layout.addWidget(lbl)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {Theme.BORDER}; max-height: 1px; border: none;")
        layout.addWidget(line)
        return card

    def _update_ui_visibility(self):
        cat = MetadataRules.get_internal_category(self.combo_category.currentText())
        media = "tv" if self.combo_media_type.currentText() == "TV Series" else "movie"
        
        # Sorter List Visibility: Only for Movie and Episode roles
        cls = self.combo_classification.currentText() if self.is_video_batch else None
        show_sorter = not self.is_video_batch or cls in ["Movie", "Episode"]
        self.left_pane_widget.setVisible(show_sorter)
        
        self.tv_card.setVisible(cat == 'video' and media == 'tv')
        self.part_card.setVisible(cat == 'video')
        self.combo_edition.setVisible(cat == 'video' and media == 'movie')
        self.chk_edition.setVisible(cat == 'video' and media == 'movie')
        
        # Update sub-types with placeholder logic
        self.combo_sub_category.blockSignals(True)
        config = MetadataRules.get_sub_type_config(cat)
        current = self.combo_sub_category.currentText()
        self.combo_sub_category.clear()
        self.combo_sub_category.addItems(config['items'])
        
        if not current and config['items']:
            self.combo_sub_category.setCurrentText(config['items'][0])
        else:
            self.combo_sub_category.setCurrentText(current)
        self.combo_sub_category.blockSignals(False)

    def _populate_list(self):
        for f in self.selected_files:
            item = QListWidgetItem(f['file_name'])
            item.setData(Qt.UserRole, f)
            self.list_widget.addItem(item)

    def _populate_parents(self):
        try:
            videos = self.engine.db.files.get_files_by_category('video')
            videos = sorted(videos, key=lambda x: x['id'], reverse=True)
            self.combo_parent.clear()
            self.combo_parent.addItem("--- Select Parent ---", None)
            for v in videos:
                self.combo_parent.addItem(v['file_name'], v['id'])
        except: pass

    def _apply_changes(self):
        target_cat = MetadataRules.get_internal_category(self.combo_category.currentText())
        target_media = "tv" if self.combo_media_type.currentText() == "TV Series" else "movie"
        
        updates_to_apply = []
        current_ep = self.spin_episode_start.value()
        current_part = self.spin_part_start.value()

        for i in range(self.list_widget.count()):
            f = self.list_widget.item(i).data(Qt.UserRole)
            updates = {'id': f['id']}
            
            if self.chk_category.isChecked(): 
                updates['category'] = target_cat
                if target_cat == 'video':
                    updates['fn_media_type'] = target_media
                    updates['parent_file_id'] = None
                    updates['sub_category'] = None
                    updates['match_status'] = 'PENDING'
                elif target_cat == 'extra':
                    updates['language'] = None
                    updates['match_status'] = None
            
            if self.chk_sub_category.isChecked(): updates['sub_category'] = self.combo_sub_category.currentText()
            if self.chk_media_type.isChecked(): updates['fn_media_type'] = target_media
            if self.chk_season.isChecked(): updates['fn_season'] = self.spin_season.value()
            if self.chk_episodes.isChecked():
                updates['fn_episode'] = str(current_ep)
                current_ep += 1
            if self.chk_parts.isChecked():
                updates['part_number'] = current_part
                current_part += 1
            if self.chk_edition.isChecked(): updates['edition'] = self.combo_edition.currentText()
            if self.chk_lang.isChecked(): updates['language'] = self.combo_lang.currentText()
            if self.chk_parent.isChecked(): updates['parent_file_id'] = self.combo_parent.currentData()

            if len(updates) > 1:
                updates_to_apply.append(updates)

        if updates_to_apply:
            try:
                self.engine.db.files.bulk_update_files(updates_to_apply)
                
                # Reactive Update: Resolve all files that might have been completed by this batch
                for up in updates_to_apply:
                    self.engine.resolver.resolve_from_local_data(up['id'])
                
                QMessageBox.information(self, "Success", f"Updated {len(updates_to_apply)} files.")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed: {e}")

