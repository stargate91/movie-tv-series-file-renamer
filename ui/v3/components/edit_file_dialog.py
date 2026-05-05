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
        self.combo_classification.addItem(T("edit_file.roles.movie"), "Movie")
        self.combo_classification.addItem(T("edit_file.roles.episode"), "Episode")
        self.combo_classification.addItem(T("edit_file.roles.bonus"), "Bonus Video")
        self.combo_classification.currentIndexChanged.connect(self._on_classification_changed)
        
        # Sub-Type
        self.st_group = QWidget()
        st_lay = QVBoxLayout(self.st_group)
        st_lay.setContentsMargins(0, 5, 0, 0)
        st_lay.addWidget(QLabel(T("edit_file.fields.type"), styleSheet="color: #94A3B8;"))
        self.combo_sub_type = QComboBox()
        self.combo_sub_type.setEditable(True)
        st_lay.addWidget(self.combo_sub_type)

        self.cat_card.layout().addWidget(QLabel(T("edit_file.fields.primary_role"), styleSheet="font-weight: bold;"))
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
        
        part_lay = QHBoxLayout()
        part_lay.addWidget(QLabel(T("edit_file.fields.part")))
        self.combo_part_type = QComboBox()
        self.combo_part_type.addItem(T("edit_file.parts.part"), "Part")
        self.combo_part_type.addItem(T("edit_file.parts.cd"), "CD")
        self.combo_part_type.addItem(T("edit_file.parts.disk"), "Disk")
        part_lay.addWidget(self.combo_part_type)
        self.spin_part = QSpinBox()
        self.spin_part.setRange(0, 99)
        part_lay.addWidget(self.spin_part)
        mv_lay.addLayout(part_lay)

        # Language
        self.lang_group = QWidget()
        lang_lay = QVBoxLayout(self.lang_group)
        lang_lay.setContentsMargins(0, 0, 0, 0)
        lang_lay.addWidget(QLabel(T("edit_file.fields.language")))
        self.combo_lang = QComboBox()
        self.combo_lang.setEditable(True)
        self.combo_lang.addItems(["ENG", "HUN", "GER", "FRA", "SPA", "ITA", "JPN"])
        lang_lay.addWidget(self.combo_lang)

        # Linking
        self.link_group = QWidget()
        link_lay = QVBoxLayout(self.link_group)
        link_lay.setContentsMargins(0, 0, 0, 0)
        link_lay.addWidget(QLabel(T("edit_file.fields.linked_to")))
        self.combo_parent = QComboBox()
        self.combo_parent.setEditable(True)
        link_lay.addWidget(self.combo_parent)

        self.details_card.layout().addWidget(self.tv_group)
        self.details_card.layout().addWidget(self.movie_group)
        self.details_card.layout().addWidget(self.lang_group)
        self.details_card.layout().addWidget(self.link_group)
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
        card.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 8px; border: 1px solid {Theme.BORDER};")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #E2E8F0; border: none;")
        layout.addWidget(lbl)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {Theme.BORDER}; max-height: 1px; border: none;")
        layout.addWidget(line)
        return card

    def _load_data(self):
        f = self.file_data
        cat = f.get('category', 'unknown')
        
        # Populate allowed categories
        self.combo_category.clear()
        allowed = MetadataRules.get_allowed_categories(cat)
        self.combo_category.addItems(allowed)
        
        # Set base category
        self.combo_category.setCurrentText(MetadataRules.get_category_label(cat))
        
        # Unified classification
        if cat in ['video', 'extra']:
            self.combo_category.hide()
            self.combo_classification.show()
            if cat == 'extra':
                self.combo_classification.setCurrentText("Bonus Video")
            else:
                if f.get('fn_media_type') == 'tv':
                    self.combo_classification.setCurrentText("Episode")
                else:
                    self.combo_classification.setCurrentText("Movie")
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
        self.spin_part.setValue(f.get('part_number') or 0)
        self.combo_lang.setCurrentText(f.get('language') or "ENG")
        
        # Update visibility
        self._update_visibility()

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
        self._update_visibility()

    def _update_visibility(self):
        cat_label = self.combo_category.currentText()
        cat_internal = MetadataRules.get_internal_category(cat_label)
        media_internal = "tv" if self.combo_media_type.currentText() == "TV Series" else "movie"
        
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
        self.combo_sub_type.addItems(config['items'])
        
        if not current and config['items']:
            self.combo_sub_type.setCurrentText(config['items'][0])
        else:
            self.combo_sub_type.setCurrentText(current)
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
        cat_label = self.combo_category.currentText()
        target_cat = MetadataRules.get_internal_category(cat_label)
        
        updates = {
            'id': self.file_data['id'],
            'category': target_cat
        }
        
        if target_cat == 'video':
            updates['fn_media_type'] = "tv" if self.combo_classification.currentText() == "Episode" else "movie"
            updates['fn_season'] = self.spin_season.value() if updates['fn_media_type'] == 'tv' else None
            updates['fn_episode'] = str(self.spin_episode.value()) if updates['fn_media_type'] == 'tv' else None
            updates['edition'] = self.combo_edition.currentText() if updates['fn_media_type'] == 'movie' else None
            updates['part_number'] = self.spin_part.value()
            updates['parent_file_id'] = None
            updates['sub_category'] = None
            updates['match_status'] = 'PENDING'
        elif target_cat == 'extra':
            updates['sub_category'] = self.combo_sub_type.currentText()
            updates['parent_file_id'] = self.combo_parent.currentData()
            updates['language'] = None
            updates['match_status'] = None
        else:
            updates['sub_category'] = self.combo_sub_type.currentText() if self.st_group.isVisible() else None
            updates['language'] = self.combo_lang.currentText() if self.lang_group.isVisible() else None
            updates['parent_file_id'] = self.combo_parent.currentData() if self.link_group.isVisible() else None

        try:
            file_id = updates.pop('id')
            self.engine.db.files.update_file(file_id, **updates)
            
            # Reactive Update: Try to fetch API metadata if we have a Series ID but just added S/E
            self.engine.resolver.resolve_from_local_data(file_id)
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, T("common.error"), f"{T('common.operation_successful')}: {e}") # Wait, error msg should be localized
            # Let's add a generic fail msg
