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
from core.i18n import T

logger = logging.getLogger(__name__)

class BatchOperationsDialog(QDialog):
    """
    Dialog for performing bulk operations on multiple files.
    Features a reorderable list and checkbox-based property overrides.
    """
    def __init__(self, engine, selected_files, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.selected_files = selected_files
        self.files_map = {f['id']: f for f in selected_files}
        
        # Detect if we should use unified classification (all video/extra)
        self.is_video_batch = all(f.get('category') in ['video', 'extra'] for f in self.selected_files)
        self.is_pure_extra = all(f.get('category') not in ['video', 'extra'] for f in self.selected_files)
        
        # Determine if we can override category (only if mixed or unknown)
        first_cat = self.selected_files[0].get('category') if self.selected_files else 'video'
        self.can_override_cat = all(f.get('category') == first_cat for f in self.selected_files)
        
        self.setWindowTitle(T("discovery.batch_operations.title", count=len(self.selected_files)))
        self.setMinimumSize(1000, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.setStyleSheet(Theme.get_main_stylesheet() + Theme.get_accent_combobox_style())
        
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
        left_layout.addWidget(QLabel(T("discovery.batch_operations.file_selection"), styleSheet=Theme.get_card_header_style()))
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setStyleSheet(Theme.get_sidebar_list_style())
        left_layout.addWidget(self.list_widget)
        self.main_layout.addWidget(self.left_pane_widget, 1)

        # RIGHT PANE: Operations
        right_pane = QVBoxLayout()
        right_pane.addWidget(QLabel(T("discovery.batch_operations.configure_props"), styleSheet=Theme.get_card_header_style()))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(Theme.get_scroll_area_transparent_style())
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)

        # --- Card 1: Category & Type ---
        self.cat_card = self._create_card(T("discovery.batch_operations.cards.category"))
        
        self.chk_category = QCheckBox(T("discovery.batch_operations.fields.override_cat"))
        self.combo_category = QComboBox()
        self.combo_category.addItem(T("discovery.batch_operations.options.categories.video"), "video")
        self.combo_category.addItem(T("discovery.batch_operations.options.categories.extra"), "extra")
        self.combo_category.addItem(T("discovery.batch_operations.options.categories.subtitle"), "subtitle")
        self.combo_category.addItem(T("discovery.batch_operations.options.categories.audio"), "audio")
        self.combo_category.addItem(T("discovery.batch_operations.options.categories.image"), "image")
        self.combo_category.addItem(T("discovery.batch_operations.options.categories.meta"), "meta")
        self.combo_category.setEnabled(False)
        self.chk_category.toggled.connect(self.combo_category.setEnabled)
        self.combo_category.currentIndexChanged.connect(self._update_ui_visibility)
        
        # Unified Classification
        self.combo_classification = QComboBox()
        self.combo_classification.addItem(T("discovery.batch_operations.options.roles.movie"), "movie")
        self.combo_classification.addItem(T("discovery.batch_operations.options.roles.episode"), "episode")
        self.combo_classification.addItem(T("discovery.batch_operations.options.roles.bonus"), "bonus")
        self.combo_classification.currentIndexChanged.connect(self._on_classification_changed)
        self.combo_classification.setEnabled(False)
        self.chk_category.toggled.connect(self.combo_classification.setEnabled)

        self.chk_sub_category = QCheckBox(T("discovery.batch_operations.fields.override_sub"))
        self.combo_sub_category = QComboBox()
        self.combo_sub_category.setEditable(False)
        # Populate later in update_ui_visibility
        self.combo_sub_category.setEnabled(False)
        self.chk_sub_category.toggled.connect(self.combo_sub_category.setEnabled)
        
        self.chk_media_type = QCheckBox(T("discovery.batch_operations.fields.media_type"))
        self.combo_media_type = QComboBox()
        self.combo_media_type.addItem(T("discovery.batch_operations.options.media_types.movie"), "movie")
        self.combo_media_type.addItem(T("discovery.batch_operations.options.media_types.tv"), "tv")
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
        
        # Populate categories based on first item if consistent
        if self.can_override_cat:
            cat = self.selected_files[0].get('category')
            allowed = MetadataRules.get_allowed_categories(cat)
            self.combo_category.clear()
            for k in allowed:
                label = T(f"discovery.batch_operations.options.categories.{k}")
                if label == f"discovery.batch_operations.options.categories.{k}": label = k.capitalize()
                self.combo_category.addItem(label, k)
            
            # If only one category is allowed (e.g. audio), disable the override checkbox
            if len(allowed) <= 1:
                self.chk_category.setEnabled(False)
                self.chk_category.setChecked(False)
                self.chk_category.setToolTip("Category is fixed for these asset types.")

        if self.is_video_batch:
            self.combo_category.hide()
            self.combo_media_type.hide()
            self.chk_media_type.hide()
        elif self.is_pure_extra:
            self.combo_classification.hide()
        else:
            self.combo_classification.hide()

        # --- Card 2: TV Series ---
        self.tv_card = self._create_card(T("discovery.batch_operations.cards.tv"))
        self.chk_season = QCheckBox(T("discovery.batch_operations.fields.set_season"))
        self.spin_season = QSpinBox()
        self.spin_season.setRange(0, 999)
        self.spin_season.setEnabled(False)
        self.chk_season.toggled.connect(self.spin_season.setEnabled)
        
        self.chk_episodes = QCheckBox(T("discovery.batch_operations.fields.renumber_ep"))
        ep_layout = QHBoxLayout()
        ep_layout.addWidget(QLabel(T("discovery.batch_operations.fields.start_ep")))
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
        self.part_card = self._create_card(T("discovery.batch_operations.cards.parts"))
        self.chk_parts = QCheckBox(T("discovery.batch_operations.fields.set_sequential_parts") or "Set Sequential Parts")
        
        p_layout = QHBoxLayout()
        p_layout.addWidget(QLabel(T("discovery.batch_operations.fields.start_val") or "Start Number:"))
        self.spin_part_start = QSpinBox()
        self.spin_part_start.setRange(1, 999)
        self.spin_part_start.setValue(1)
        self.spin_part_start.setEnabled(False)
        p_layout.addWidget(self.spin_part_start)
        p_layout.addStretch()
        
        self.chk_parts.toggled.connect(self.spin_part_start.setEnabled)
        
        self.part_card.layout().addWidget(self.chk_parts)
        self.part_card.layout().addLayout(p_layout)
        scroll_layout.addWidget(self.part_card)

        # --- Card 4: Tags & Linking ---
        self.meta_card = self._create_card(T("discovery.batch_operations.cards.meta"))
        self.chk_edition = QCheckBox(T("discovery.batch_operations.fields.set_edition"))
        self.lbl_edition = QLabel(T("discovery.batch_operations.fields.edition_label")) # Backing for edit_dialog similarity
        self.combo_edition = QComboBox()
        self.combo_edition.setEditable(False)
        self.combo_edition.addItem("", None)
        self.combo_edition.addItem(T("common.editions.theatrical"), "Theatrical")
        self.combo_edition.addItem(T("common.editions.directors_cut"), "Director's Cut")
        self.combo_edition.addItem(T("common.editions.extended"), "Extended")
        self.combo_edition.addItem(T("common.editions.remastered"), "Remastered")
        self.combo_edition.addItem(T("common.editions.uncut"), "Uncut")
        self.combo_edition.setEnabled(False)
        self.chk_edition.toggled.connect(self.combo_edition.setEnabled)

        self.chk_lang = QCheckBox(T("discovery.batch_operations.fields.override_lang"))
        self.combo_lang = QComboBox()
        self.combo_lang.setEditable(False)
        self.combo_lang.addItem("", None)
        for code in ["eng", "hun", "ger", "fra", "spa", "ita", "jpn"]:
            label = T(f"common.languages.{code}")
            self.combo_lang.addItem(label, code.upper())
        self.combo_lang.setEnabled(False)
        self.chk_lang.toggled.connect(self.combo_lang.setEnabled)

        self.chk_parent = QCheckBox(T("discovery.batch_operations.fields.link_parent"))
        self.combo_parent = QComboBox()
        self.combo_parent.setEnabled(False)
        self.chk_parent.toggled.connect(self.combo_parent.setEnabled)

        self.chk_metadata_lang = QCheckBox(T("discovery.batch_operations.fields.override_metadata_lang") or "Override Metadata Lang")
        self.combo_metadata_lang = QComboBox()
        self.combo_metadata_lang.addItem(T("common.languages.default") or "Default (Global)", None)
        for code in ["hu-HU", "en-US", "de-DE", "fr-FR", "es-ES", "it-IT", "ja-JP", "ko-KR"]:
            self.combo_metadata_lang.addItem(code, code)
        self.combo_metadata_lang.setEnabled(False)
        self.chk_metadata_lang.toggled.connect(self.combo_metadata_lang.setEnabled)

        self.meta_card.layout().addWidget(self.chk_edition)
        self.meta_card.layout().addWidget(self.combo_edition)
        self.meta_card.layout().addWidget(self.chk_lang)
        self.meta_card.layout().addWidget(self.combo_lang)
        self.meta_card.layout().addWidget(self.chk_metadata_lang)
        self.meta_card.layout().addWidget(self.combo_metadata_lang)
        self.meta_card.layout().addWidget(self.chk_parent)
        self.meta_card.layout().addWidget(self.combo_parent)
        scroll_layout.addWidget(self.meta_card)

        scroll.setWidget(scroll_content)
        right_pane.addWidget(scroll)

        # Buttons
        btns = QHBoxLayout()
        btn_apply = QPushButton(T("discovery.batch_operations.apply_btn"))
        btn_apply.setMinimumHeight(40)
        btn_apply.setStyleSheet(Theme.get_primary_button_style())
        btn_apply.clicked.connect(self._apply_changes)
        btns.addWidget(btn_apply)
        right_pane.addLayout(btns)

        self.main_layout.addLayout(right_pane, 2)
        self._load_initial_data()
        self._update_ui_visibility()

    def _get_consensus(self, key):
        values = set()
        for f in self.selected_files:
            val = f.get(key)
            # Normalize language for comparison
            if key == 'language':
                val = (val or "").upper()
                # 2-to-3 map for consensus check
                mapping = {"HU": "HUN", "EN": "ENG", "DE": "GER", "FR": "FRA", "ES": "SPA", "IT": "ITA", "JA": "JPN"}
                val = mapping.get(val, val)
            values.add(val)
        return list(values)[0] if len(values) == 1 else None

    def _load_initial_data(self):
        if not self.selected_files: return
        
        # 1. Category Consensus
        cat = self._get_consensus('category')
        if cat:
            self._set_combo_by_data(self.combo_category, cat)
            if self.is_video_batch:
                if cat == 'extra': self._set_combo_by_data(self.combo_classification, "bonus")
                else:
                    mtype = self._get_consensus('fn_media_type')
                    if mtype == 'tv': self._set_combo_by_data(self.combo_classification, "episode")
                    elif mtype == 'movie': self._set_combo_by_data(self.combo_classification, "movie")
        
        # 2. Sub-type Consensus
        sub = self._get_consensus('sub_category')
        if sub:
            idx = self.combo_sub_category.findData(sub)
            if idx >= 0: self.combo_sub_category.setCurrentIndex(idx)
        else:
            self.combo_sub_category.setCurrentIndex(0)
            
        # 3. TV Info Consensus
        season = self._get_consensus('fn_season')
        if season is not None: self.spin_season.setValue(int(season))
        
        # 4. Edition Consensus
        ed = self._get_consensus('edition')
        if ed:
            idx = self.combo_edition.findData(ed)
            if idx >= 0: self.combo_edition.setCurrentIndex(idx)
        else:
            self.combo_edition.setCurrentIndex(0)

        # 5. Language Consensus
        lang = self._get_consensus('language')
        if lang:
            # We already normalized it in _get_consensus to 3-letter if it was in map
            self._set_combo_by_data(self.combo_lang, lang)
        else:
            self.combo_lang.setCurrentIndex(0)
        
        # 6. Parent Consensus
        parent_id = self._get_consensus('parent_file_id')
        if parent_id:
            self._initial_parent_id = parent_id

    def _on_classification_changed(self):
        cls = self.combo_classification.currentData()
        if cls == "movie":
            self._set_combo_by_data(self.combo_category, "video")
            self._set_combo_by_data(self.combo_media_type, "movie")
        elif cls == "episode":
            self._set_combo_by_data(self.combo_category, "video")
            self._set_combo_by_data(self.combo_media_type, "tv")
        elif cls == "bonus":
            self._set_combo_by_data(self.combo_category, "extra")
        self._update_ui_visibility()

    def _set_combo_by_data(self, combo, data):
        idx = combo.findData(data)
        if idx >= 0: combo.setCurrentIndex(idx)

    def _create_card(self, title):
        card = QFrame()
        card.setStyleSheet(Theme.get_batch_card_style())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        lbl = QLabel(title)
        lbl.setStyleSheet(Theme.get_card_header_style())
        layout.addWidget(lbl)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {Theme.BORDER}; max-height: 1px; border: none;")
        layout.addWidget(line)
        return card

    def _update_ui_visibility(self):
        cat = self.combo_category.currentData()
        media = self.combo_media_type.currentData()
        
        # Sorter List Visibility: Only for Movie and Episode roles
        cls = self.combo_classification.currentData() if self.is_video_batch else None
        show_sorter = (self.is_video_batch and cls in ["movie", "episode"])
        self.left_pane_widget.setVisible(show_sorter)
        
        visible_fields = MetadataRules.get_visible_fields(cat, media)
        
        # Hide Category Card if no interactive fields are visible (except the fixed category info)
        has_sub_type = 'sub_type' in visible_fields
        has_media_type = ('media_type' in visible_fields or (cat == 'video')) and not self.is_pure_extra
        
        # If we can't override category and have no sub-type or media-type to show, hide the card
        if hasattr(self, 'cat_card'):
            allowed_cats = MetadataRules.get_allowed_categories(cat)
            # We show it ONLY if:
            # 1. We can actually switch to another category (len > 1)
            # 2. OR we have a sub-type to configure
            # 3. OR we have a media type to configure (videos only)
            show_cat_card = (len(allowed_cats) > 1) or has_sub_type or has_media_type
            
            # Special case: if is_video_batch is true, we always show it because classification combo is there
            if self.is_video_batch:
                show_cat_card = True
                
            self.cat_card.setVisible(show_cat_card)

        if hasattr(self, 'tv_card'):
            self.tv_card.setVisible(cat == 'video' and media == 'tv')
        if hasattr(self, 'part_card'):
            self.part_card.setVisible(cat == 'video')
        
        has_sub_type = 'sub_type' in visible_fields
        if hasattr(self, 'chk_sub_category'): self.chk_sub_category.setVisible(has_sub_type)
        if hasattr(self, 'combo_sub_category'): self.combo_sub_category.setVisible(has_sub_type)
        
        has_edition = 'edition' in visible_fields
        if hasattr(self, 'combo_edition'): self.combo_edition.setVisible(has_edition)
        if hasattr(self, 'chk_edition'): self.chk_edition.setVisible(has_edition)
        
        # Language fields
        has_lang = 'language' in visible_fields
        if hasattr(self, 'chk_lang'): self.chk_lang.setVisible(has_lang)
        if hasattr(self, 'combo_lang'): self.combo_lang.setVisible(has_lang)
        
        has_target_lang = 'target_lang' in visible_fields
        if hasattr(self, 'chk_metadata_lang'): self.chk_metadata_lang.setVisible(has_target_lang)
        if hasattr(self, 'combo_metadata_lang'): self.combo_metadata_lang.setVisible(has_target_lang)
        
        has_linking = 'linking' in visible_fields
        if hasattr(self, 'chk_parent'): self.chk_parent.setVisible(has_linking)
        if hasattr(self, 'combo_parent'): self.combo_parent.setVisible(has_linking)

        # Media Type (Videos only)
        # Note: metadata_rules.py returns this for 'video' category.
        # But here we should also check if it's explicitly allowed.
        has_media_type = 'media_type' in visible_fields or (cat == 'video')
        # However, for pure extras (metadata, etc), we definitely want to hide it.
        if self.is_pure_extra: has_media_type = False
        
        if hasattr(self, 'chk_media_type'): self.chk_media_type.setVisible(has_media_type)
        if hasattr(self, 'combo_media_type'): self.combo_media_type.setVisible(has_media_type)
        
        # Update sub-types with placeholder logic
        if hasattr(self, 'combo_sub_category'):
            self.combo_sub_category.blockSignals(True)
            config = MetadataRules.get_sub_type_config(cat)
            current_data = self.combo_sub_category.currentData()
            self.combo_sub_category.clear()
            self.combo_sub_category.addItem("", None)
            for item_key in config['items']:
                label = T(f"discovery.extras.subtypes.{item_key}")
                if label == f"discovery.extras.subtypes.{item_key}":
                    label = item_key.title()
                self.combo_sub_category.addItem(label, item_key)
            
            if current_data:
                idx = self.combo_sub_category.findData(current_data)
                if idx >= 0: self.combo_sub_category.setCurrentIndex(idx)
                else: self.combo_sub_category.setCurrentIndex(0)
            else:
                self.combo_sub_category.setCurrentIndex(0) # Default to empty
            self.combo_sub_category.blockSignals(False)

    def _populate_list(self):
        for f in self.selected_files:
            item = QListWidgetItem(f['file_name'])
            item.setData(Qt.UserRole, f['id'])
            self.list_widget.addItem(item)

    def _populate_parents(self):
        try:
            videos = self.engine.db.files.get_files_by_category('video')
            videos = sorted(videos, key=lambda x: x['id'], reverse=True)
            self.combo_parent.clear()
            self.combo_parent.addItem(T("discovery.batch_operations.fields.select_parent"), None)
            for v in videos:
                self.combo_parent.addItem(v['file_name'], v['id'])
        except: pass

    def _apply_changes(self):
        target_cat = self.combo_category.currentData()
        target_media = self.combo_media_type.currentData()
        
        updates_to_apply = []
        current_ep = self.spin_episode_start.value()
        current_part = self.spin_part_start.value()

        for i in range(self.list_widget.count()):
            file_id = self.list_widget.item(i).data(Qt.UserRole)
            f = self.files_map.get(file_id)
            if not f: continue
            
            updates = {'id': file_id}
            
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
            
            if self.chk_sub_category.isChecked(): updates['sub_category'] = self.combo_sub_category.currentData()
            if self.chk_media_type.isChecked(): updates['fn_media_type'] = target_media
            if self.chk_season.isChecked(): updates['fn_season'] = self.spin_season.value()
            if self.chk_episodes.isChecked():
                updates['fn_episode'] = str(current_ep)
                current_ep += 1
            if self.chk_parts.isChecked():
                updates['part'] = str(current_part)
                current_part += 1
            if self.chk_edition.isChecked(): updates['edition'] = self.combo_edition.currentData()
            if self.chk_lang.isChecked(): updates['language'] = self.combo_lang.currentData()
            if self.chk_metadata_lang.isChecked(): updates['target_language'] = self.combo_metadata_lang.currentData()
            if self.chk_parent.isChecked(): updates['parent_file_id'] = self.combo_parent.currentData()

            if len(updates) > 1:
                updates_to_apply.append(updates)

        if updates_to_apply:
            try:
                self.engine.db.files.bulk_update_files(updates_to_apply)
                
                # Reactive Update: Resolve all files that might have been completed by this batch
                for up in updates_to_apply:
                    self.engine.resolver.resolve_from_local_data(up['id'])
                
                QMessageBox.information(self, T("common.success"), T("discovery.batch_resolve.success_msg", count=len(updates_to_apply))) # Reuse msg
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, T("common.error"), f"Failed: {e}")

