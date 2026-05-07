from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QFrame, QCheckBox, QWidget
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab
from ui.v3.components.template_input import TemplateLineEdit
from core.i18n import T

class ExtrasTab(BaseSettingsTab):
    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # --- Header & Master Toggle ---
        header = QLabel(T("settings.extras.header"))
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)
        
        self.enable_extras_cb = QCheckBox(T("settings.extras.fields.enable_extras"))
        self.enable_extras_cb.setStyleSheet(Theme.get_master_toggle_style())
        self.enable_extras_cb.setChecked(self.engine.config.settings.enable_extras)
        layout.addWidget(self.enable_extras_cb)
        
        layout.addSpacing(10)
        layout.addWidget(Theme.create_hline())
        layout.addSpacing(10)

        # --- Main Content Container ---
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(30)
        layout.addWidget(self.content_widget)

        # --- Section: Extensions ---
        self.content_layout.addWidget(self._create_section_header(T("settings.extras.sections.extensions")))
        
        ext_box = QFrame()
        ext_box.setStyleSheet(Theme.get_info_box_style())
        e_layout = QVBoxLayout(ext_box)
        
        self.ext_inputs = {}
        ext_configs = [
            (T("settings.extras.fields.subtitles"), "subtitle_extensions", self.engine.config.settings.subtitle_extensions),
            (T("settings.extras.fields.audio"), "audio_extensions", self.engine.config.settings.audio_extensions),
            (T("settings.extras.fields.images"), "image_extensions", self.engine.config.settings.image_extensions),
            (T("settings.extras.fields.metadata"), "metadata_extensions", self.engine.config.settings.metadata_extensions)
        ]
        
        for label, key, val in ext_configs:
            row = QHBoxLayout()
            l_lbl = QLabel(f"<b>{label}:</b>")
            l_lbl.setFixedWidth(150)
            l_lbl.setStyleSheet(Theme.get_input_label_style())
            
            v_input = QLineEdit(val)
            v_input.setStyleSheet(Theme.get_settings_input_style())
            self.ext_inputs[key] = v_input
            
            row.addWidget(l_lbl)
            row.addWidget(v_input)
            e_layout.addLayout(row)
            
        self.content_layout.addWidget(ext_box)
        self.content_layout.addSpacing(10)
        self.content_layout.addWidget(Theme.create_hline())
        self.content_layout.addSpacing(10)

        # --- Section: Types ---
        self.content_layout.addWidget(self._create_section_header(T("settings.extras.sections.handling")))
        
        self.extra_combos = {}
        self.extra_templates = {}
        types = [
            (T("settings.extras.fields.video_clips"), "action_extra_video", "template_extra_video", "extras"),
            (T("settings.extras.fields.subtitles"), "action_extra_subtitle", "template_extra_subtitle", "extras_lang"),
            (T("settings.extras.fields.audio"), "action_extra_audio", "template_extra_audio", "extras_lang"),
            (T("settings.extras.fields.images_posters"), "action_extra_image", "template_extra_image", "extras"),
            (T("settings.extras.fields.metadata"), "action_extra_metadata", "template_extra_metadata", "extras")
        ]
        
        for label_text, setting_key, tpl_key, tpl_context in types:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(Theme.get_card_header_style())
            lbl.setFixedWidth(150)
            
            combo = QComboBox()
            combo.setStyleSheet(Theme.get_combobox_style())
            combo.setFixedWidth(120)
            combo.addItem(T("settings.extras.actions.rename"), "rename")
            combo.addItem(T("settings.extras.actions.skip"), "skip")
            combo.addItem(T("settings.extras.actions.delete"), "delete")
            
            current_val = getattr(self.engine.config.settings, setting_key, "rename")
            idx = combo.findData(current_val)
            if idx >= 0: combo.setCurrentIndex(idx)
                
            self.extra_combos[setting_key] = combo
            
            tpl_input = TemplateLineEdit(context=tpl_context)
            tpl_input.setText(getattr(self.engine.config.settings, tpl_key, ""))
            tpl_input.setEnabled(current_val == "rename")
            
            self.extra_templates[tpl_key] = tpl_input
            
            combo.currentIndexChanged.connect(lambda _, c=combo, t=tpl_input: t.setEnabled(c.currentData() == "rename"))
            
            row.addWidget(lbl)
            row.addWidget(combo)
            row.addWidget(tpl_input)
            self.content_layout.addLayout(row)
        # Help section removed - variables are now in the smart input fields

        # --- Section: Folder Placement ---
        self.content_layout.addWidget(self._create_section_header(T("settings.extras.sections.placement")))
        
        mode_row = QHBoxLayout()
        mode_lbl = QLabel(T("settings.extras.fields.folder_mode"))
        mode_lbl.setStyleSheet(Theme.get_card_header_style())
        self.extras_mode_combo = QComboBox()
        self.extras_mode_combo.setStyleSheet(Theme.get_combobox_style())
        self.extras_mode_combo.setFixedWidth(200)
        self.extras_mode_combo.addItem(T("settings.extras.modes.none"), "none")
        self.extras_mode_combo.addItem(T("settings.extras.modes.single"), "single")
        self.extras_mode_combo.addItem(T("settings.extras.modes.categorized"), "categorized")
        
        idx = self.extras_mode_combo.findData(self.engine.config.settings.extras_folder_mode)
        if idx >= 0: self.extras_mode_combo.setCurrentIndex(idx)
        
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.extras_mode_combo)
        mode_row.addStretch()
        self.content_layout.addLayout(mode_row)
        
        self.extras_name_input = self._create_input_group(T("settings.extras.fields.folder_name"), self.engine.config.settings.extras_folder_name, "Extras")
        self.content_layout.addLayout(self.extras_name_input['layout'])
        
        def update_name_state():
            self.extras_name_input['edit'].setEnabled(self.extras_mode_combo.currentData() == "single")
        
        self.extras_mode_combo.currentIndexChanged.connect(update_name_state)
        update_name_state()

        self.content_layout.addStretch()

        # Connect Global Toggle
        self.enable_extras_cb.toggled.connect(self._update_ui_state)
        self._update_ui_state(self.enable_extras_cb.isChecked())

    def _update_ui_state(self, enabled):
        self.content_widget.setEnabled(enabled)
        # Optional: update opacity to make it more obvious
        self.content_widget.setWindowOpacity(1.0 if enabled else 0.5)

    def save_to_settings(self, s):
        s.enable_extras = self.enable_extras_cb.isChecked()
        for key, combo in self.extra_combos.items():
            setattr(s, key, combo.currentData())
        for key, tpl in self.extra_templates.items():
            setattr(s, key, tpl.text())
        for key, inp in self.ext_inputs.items():
            setattr(s, key, inp.text())
        s.extras_folder_mode = self.extras_mode_combo.currentData()
        s.extras_folder_name = self.extras_name_input['edit'].text()
