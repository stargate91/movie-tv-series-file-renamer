import os
import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QWidget, QComboBox, 
                             QSpinBox, QFrame, QMessageBox, QLineEdit)
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from core.engine.metadata_rules import MetadataRules
from core.i18n import T

logger = logging.getLogger(__name__)

class EditFileDialog(QDialog):
    """
    Dedicated dialog for editing metadata for a single file.
    Optimized for clarity and speed without batch-processing complexity.
    """
    def __init__(self, parent, engine, file_data):
        super().__init__(parent)
        self.engine = engine
        self.file_data = file_data
        
        self.setWindowTitle(T("edit_file.title", filename=file_data['file_name']))
        self.setMinimumSize(500, 600)
        self.setStyleSheet(Theme.get_main_stylesheet())
        
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)

        # 1. Classification Section
        self.cat_card = self._create_card(T("edit_file.sections.classification"))
        
        # Hidden standard combos (used as backing store)
        self.combo_category = QComboBox()
        # Items will be populated dynamically in _load_data
        self.combo_category.hide()
        self.combo_media_type = QComboBox()
        self.combo_media_type.addItem(T("common.types.movie"), "movie")
        self.combo_media_type.addItem(T("common.types.tv"), "tv")
        self.combo_media_type.hide()

        # Unified Classification
        self.combo_classification = QComboBox()
        self.combo_classification.addItem(T("edit_file.roles.movie"), "movie")
        self.combo_classification.addItem(T("edit_file.roles.episode"), "episode")
        self.combo_classification.addItem(T("edit_file.roles.bonus"), "bonus")
        self.combo_classification.currentIndexChanged.connect(self._on_classification_changed)
        
        # Sub-Type
        self.st_group = QWidget()
        st_lay = QVBoxLayout(self.st_group)
        st_lay.setContentsMargins(0, 5, 0, 0)
        st_lay.addWidget(QLabel(T("edit_file.fields.type"), styleSheet=Theme.get_status_label_style()))
        self.combo_sub_type = QComboBox()
        self.combo_sub_type.setEditable(True)
        st_lay.addWidget(self.combo_sub_type)

        self.cat_card.layout().addWidget(QLabel(T("edit_file.fields.primary_role"), styleSheet=Theme.get_card_header_style()))
        self.cat_card.layout().addWidget(self.combo_classification)
        self.cat_card.layout().addWidget(self.combo_category) # Visible for non-video categories
        self.cat_card.layout().addWidget(self.st_group)
        layout.addWidget(self.cat_card)

        # 2. Details Section (Dynamic)
        self.details_card = self._create_card(T("edit_file.sections.details"))
        
        # TV Info
        self.tv_group = QWidget()
        tv_lay = QHBoxLayout(self.tv_group)
        tv_lay.setContentsMargins(0, 0, 0, 0)
        tv_lay.addWidget(QLabel(T("edit_file.fields.season")))
        self.spin_season = QSpinBox()
        self.spin_season.setRange(0, 999)
        tv_lay.addWidget(self.spin_season)
        tv_lay.addWidget(QLabel(T("edit_file.fields.episode")))
        self.spin_episode = QSpinBox()
        self.spin_episode.setRange(0, 9999)
        tv_lay.addWidget(self.spin_episode)

        self.movie_group = QWidget()
        mv_lay = QVBoxLayout(self.movie_group)
        mv_lay.setContentsMargins(0, 0, 0, 0)
        self.lbl_edition = QLabel(T("edit_file.fields.edition"))
        mv_lay.addWidget(self.lbl_edition)
        self.combo_edition = QComboBox()
        self.combo_edition.setEditable(True)
        self.combo_edition.addItem("")
        self.combo_edition.addItem(T("edit_file.editions.theatrical"), "Theatrical")
        self.combo_edition.addItem(T("edit_file.editions.directors_cut"), "Director's Cut")
        self.combo_edition.addItem(T("edit_file.editions.extended"), "Extended")
        self.combo_edition.addItem(T("edit_file.editions.remastered"), "Remastered")
        self.combo_edition.addItem(T("edit_file.editions.uncut"), "Uncut")
        mv_lay.addWidget(self.combo_edition)
        
        part_lay = QVBoxLayout()
        part_lay.setContentsMargins(0, 5, 0, 0)
        part_lay.addWidget(QLabel(T("edit_file.fields.part") or "Part ID (1, A, II):", styleSheet=Theme.get_status_label_style()))
        self.edit_part = QLineEdit()
        self.edit_part.setPlaceholderText("e.g. 1, A, II")
        part_lay.addWidget(self.edit_part)
        mv_lay.addLayout(part_lay)

        # Language
        self.lang_group = QWidget()
        lang_lay = QVBoxLayout(self.lang_group)
        lang_lay.setContentsMargins(0, 0, 0, 0)
        lang_lay.addWidget(QLabel(T("edit_file.fields.language")))
        self.combo_lang = QComboBox()
        self.combo_lang.setEditable(True)
        for code in ["eng", "hun", "ger", "fra", "spa", "ita", "jpn"]:
            self.combo_lang.addItem(T(f"common.languages.{code}"), code.upper())
        lang_lay.addWidget(self.combo_lang)

        # Parent Link
        self.link_group = QWidget()
        link_lay = QVBoxLayout(self.link_group)
        link_lay.setContentsMargins(0, 0, 0, 0)
        link_lay.addWidget(QLabel(T("edit_file.fields.parent_link") or "Link to Parent:"))
        self.combo_parent = QComboBox()
        link_lay.addWidget(self.combo_parent)

        # Metadata Language Override
        self.metadata_lang_group = QWidget()
        ml_lay = QVBoxLayout(self.metadata_lang_group)
        ml_lay.setContentsMargins(0, 0, 0, 0)
        ml_lay.addWidget(QLabel(T("edit_file.fields.metadata_language") or "Metadata Language:"))
        self.combo_metadata_lang = QComboBox()
        self.combo_metadata_lang.addItem(T("common.languages.default") or "Default (Global)", None)
        for code in ["hu-HU", "en-US", "de-DE", "fr-FR", "es-ES", "it-IT", "ja-JP", "ko-KR"]:
            self.combo_metadata_lang.addItem(code, code)
        ml_lay.addWidget(self.combo_metadata_lang)

        self.details_card.layout().addWidget(self.tv_group)
        self.details_card.layout().addWidget(self.movie_group)
        self.details_card.layout().addWidget(self.lang_group)
        self.details_card.layout().addWidget(self.link_group)
        self.details_card.layout().addWidget(self.metadata_lang_group)
        layout.addWidget(self.details_card)

        layout.addStretch()

        # Buttons
        btns = QHBoxLayout()
        btn_cancel = QPushButton(T("common.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton(T("edit_file.save_btn"))
        btn_save.setMinimumHeight(40)
        btn_save.setStyleSheet(Theme.get_primary_button_style())
        btn_save.clicked.connect(self._apply_changes)
        
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

        # Populate parents in background
        self._populate_parents()

    def _create_card(self, title):
        card = QFrame()
        card.setStyleSheet(Theme.get_batch_card_style())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        lbl = QLabel(title)
        lbl.setStyleSheet(Theme.get_card_header_style())
        layout.addWidget(lbl)
        
        layout.addWidget(Theme.create_hline())
        return card

    def _load_data(self):
        f = self.file_data
        cat = f.get('category', 'unknown')
        
        # Populate allowed categories
        self.combo_category.clear()
        allowed_keys = MetadataRules.get_allowed_categories(cat)
        for ck in allowed_keys:
            label = T(f"discovery.batch_operations.options.categories.{ck}")
            if label == f"discovery.batch_operations.options.categories.{ck}":
                label = ck.capitalize()
            self.combo_category.addItem(label, ck)
        
        # Set base category
        self._set_combo_by_data(self.combo_category, cat)
        
        # Unified classification
        if cat in ['video', 'extra']:
            self.combo_category.hide()
            self.combo_classification.show()
            if cat == 'extra':
                self._set_combo_by_data(self.combo_classification, "bonus")
            else:
                if f.get('fn_media_type') == 'tv':
                    self._set_combo_by_data(self.combo_classification, "episode")
                else:
                    self._set_combo_by_data(self.combo_classification, "movie")
        else:
            self.combo_classification.hide()
            self.combo_category.show()

        # Sub-type
        self.combo_sub_type.setCurrentText(f.get('sub_category') or "")
        
        # Details
        self.spin_season.setValue(f.get('fn_season') or 0)
        ep_val = f.get('fn_episode')
        self.spin_episode.setValue(int(ep_val) if str(ep_val or "").isdigit() else 0)
        self.combo_edition.setCurrentText(f.get('edition') or "")
        self.edit_part.setText(str(f.get('part') or ""))
        self._set_combo_by_data(self.combo_lang, (f.get('language') or "ENG").upper())
        self._set_combo_by_data(self.combo_metadata_lang, f.get('target_language'))
        
        # Update visibility
        self._update_visibility()

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
        self._update_visibility()

    def _set_combo_by_data(self, combo, data):
        idx = combo.findData(data)
        if idx >= 0: combo.setCurrentIndex(idx)

    def _update_visibility(self):
        cat_internal = self.combo_category.currentData()
        media_internal = self.combo_media_type.currentData()
        
        visible_fields = MetadataRules.get_visible_fields(cat_internal, media_internal)
        
        # Section Visibility
        self.st_group.setVisible('sub_type' in visible_fields)
        self.tv_group.setVisible('season' in visible_fields or 'episodes' in visible_fields)
        
        # Movie/Parts Group
        has_edition = 'edition' in visible_fields
        has_parts = 'parts' in visible_fields
        self.movie_group.setVisible(has_edition or has_parts)
        self.combo_edition.setVisible(has_edition)
        # We might need a label for edition to hide it too
        if hasattr(self, 'lbl_edition'): self.lbl_edition.setVisible(has_edition)

        self.lang_group.setVisible('language' in visible_fields)
        self.link_group.setVisible('linking' in visible_fields)
        
        # Update sub-type items if category changed
        self.combo_sub_type.blockSignals(True)
        config = MetadataRules.get_sub_type_config(cat_internal)
        current = self.combo_sub_type.currentText()
        self.combo_sub_type.clear()
        for item_key in config['items']:
            label = T(f"discovery.extras.subtypes.{item_key}")
            if label == f"discovery.extras.subtypes.{item_key}":
                label = item_key.title()
            self.combo_sub_type.addItem(label, item_key)
        
        if not current:
            if config['default']:
                idx = self.combo_sub_type.findData(config['default'])
                if idx >= 0: self.combo_sub_type.setCurrentIndex(idx)
        else:
            idx = self.combo_sub_type.findText(current)
            if idx >= 0: self.combo_sub_type.setCurrentIndex(idx)
            else: self.combo_sub_type.setCurrentText(current)
        self.combo_sub_type.blockSignals(False)

    def _populate_parents(self):
        try:
            videos = self.engine.db.files.get_files_by_category('video')
            videos = sorted(videos, key=lambda x: x['id'], reverse=True)
            self.combo_parent.clear()
            self.combo_parent.addItem(T("edit_file.parent_select"), None)
            for v in videos:
                self.combo_parent.addItem(v['file_name'], v['id'])
            
            # Set current parent
            parent_id = self.file_data.get('parent_file_id')
            if parent_id:
                for i in range(self.combo_parent.count()):
                    if self.combo_parent.itemData(i) == parent_id:
                        self.combo_parent.setCurrentIndex(i)
                        break
        except: pass

    def _apply_changes(self):
        target_cat = self.combo_category.currentData()
        
        updates = {
            'id': self.file_data['id'],
            'category': target_cat
        }
        
        if target_cat == 'video':
            updates['fn_media_type'] = "tv" if self.combo_classification.currentData() == "episode" else "movie"
            updates['fn_season'] = self.spin_season.value() if updates['fn_media_type'] == 'tv' else None
            updates['fn_episode'] = str(self.spin_episode.value()) if updates['fn_media_type'] == 'tv' else None
            updates['edition'] = self.combo_edition.currentText() if updates['fn_media_type'] == 'movie' else None
            updates['part'] = self.edit_part.text().strip()
            updates['parent_file_id'] = None
            updates['sub_category'] = None
            updates['match_status'] = 'PENDING'
        elif target_cat == 'extra':
            updates['sub_category'] = self.combo_sub_type.currentText()
            updates['parent_file_id'] = self.combo_parent.currentData()
            updates['language'] = None
            updates['match_status'] = None
        else:
            updates['sub_category'] = self.combo_sub_type.currentData() if self.st_group.isVisible() else None
            updates['language'] = self.combo_lang.currentData() if self.lang_group.isVisible() else None
            updates['target_language'] = self.combo_metadata_lang.currentData()
            updates['parent_file_id'] = self.combo_parent.currentData() if self.link_group.isVisible() else None

        try:
            file_id = updates.pop('id')
            self.engine.db.files.update_file(file_id, **updates)
            
            # Reactive Update: Try to fetch API metadata if we have a Series ID but just added S/E
            self.engine.resolver.resolve_from_local_data(file_id)
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, T("common.error"), f"{e}")
