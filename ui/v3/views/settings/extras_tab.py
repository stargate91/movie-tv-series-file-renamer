from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QFrame, QCheckBox, QWidget
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab
from ui.v3.components.template_input import TemplateLineEdit

class ExtrasTab(BaseSettingsTab):
    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # --- Header & Global Toggle ---
        header_row = QHBoxLayout()
        header = QLabel("Extras Settings")
        header.setStyleSheet(Theme.get_page_header_style())
        header_row.addWidget(header)
        header_row.addStretch()
        
        self.enable_extras_cb = QCheckBox("Enable Extras Handling")
        self.enable_extras_cb.setChecked(self.engine.config.settings.enable_extras)
        header_row.addWidget(self.enable_extras_cb)
        layout.addLayout(header_row)
        
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
        self.content_layout.addWidget(self._create_section_header("MONITORED EXTENSIONS"))
        
        ext_box = QFrame()
        ext_box.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.SURFACE_LIGHT};
                border: 1px solid {Theme.BORDER};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        e_layout = QVBoxLayout(ext_box)
        
        self.ext_inputs = {}
        ext_configs = [
            ("Subtitles", "subtitle_extensions", self.engine.config.settings.subtitle_extensions),
            ("Audio Tracks", "audio_extensions", self.engine.config.settings.audio_extensions),
            ("Images", "image_extensions", self.engine.config.settings.image_extensions),
            ("Metadata / NFO", "metadata_extensions", self.engine.config.settings.metadata_extensions)
        ]
        
        for label, key, val in ext_configs:
            row = QHBoxLayout()
            l_lbl = QLabel(f"<b>{label}:</b>")
            l_lbl.setFixedWidth(150)
            l_lbl.setStyleSheet(f"color: {Theme.TEXT_MAIN}; font-size: 13px;")
            
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
        self.content_layout.addWidget(self._create_section_header("EXTRAS HANDLING"))
        
        self.extra_combos = {}
        self.extra_templates = {}
        types = [
            ("Video Clips", "action_extra_video", "template_extra_video"),
            ("Subtitles", "action_extra_subtitle", "template_extra_subtitle"),
            ("Audio Tracks", "action_extra_audio", "template_extra_audio"),
            ("Images / Posters", "action_extra_image", "template_extra_image"),
            ("Metadata / NFO", "action_extra_metadata", "template_extra_metadata")
        ]
        
        for label_text, setting_key, tpl_key in types:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(Theme.get_card_header_style())
            lbl.setFixedWidth(150)
            
            combo = QComboBox()
            combo.setStyleSheet(Theme.get_combobox_style())
            combo.setFixedWidth(120)
            combo.addItems(["rename", "skip", "delete"])
            
            current_val = getattr(self.engine.config.settings, setting_key, "rename")
            idx = combo.findText(current_val)
            if idx >= 0: combo.setCurrentIndex(idx)
                
            self.extra_combos[setting_key] = combo
            
            tpl_input = TemplateLineEdit(context="all")
            tpl_input.setText(getattr(self.engine.config.settings, tpl_key, ""))
            tpl_input.setEnabled(current_val == "rename")
            
            self.extra_templates[tpl_key] = tpl_input
            
            combo.currentTextChanged.connect(lambda text, t=tpl_input: t.setEnabled(text == "rename"))
            
            row.addWidget(lbl)
            row.addWidget(combo)
            row.addWidget(tpl_input)
            self.content_layout.addLayout(row)
        # Help section removed - variables are now in the smart input fields

        # --- Section: Folder Placement ---
        self.content_layout.addWidget(self._create_section_header("EXTRAS FOLDER PLACEMENT"))
        
        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Folder Mode:")
        mode_lbl.setStyleSheet(Theme.get_card_header_style())
        self.extras_mode_combo = QComboBox()
        self.extras_mode_combo.setStyleSheet(Theme.get_combobox_style())
        self.extras_mode_combo.setFixedWidth(200)
        self.extras_mode_combo.addItem("Next to the main video file", "none")
        self.extras_mode_combo.addItem("Single 'Extras' folder", "single")
        self.extras_mode_combo.addItem("Categorized subfolders", "categorized")
        
        idx = self.extras_mode_combo.findData(self.engine.config.settings.extras_folder_mode)
        if idx >= 0: self.extras_mode_combo.setCurrentIndex(idx)
        
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.extras_mode_combo)
        mode_row.addStretch()
        self.content_layout.addLayout(mode_row)
        
        self.extras_name_input = self._create_input_group("Extras Folder Name", self.engine.config.settings.extras_folder_name, "Extras")
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
            setattr(s, key, combo.currentText())
        for key, tpl in self.extra_templates.items():
            setattr(s, key, tpl.text())
        for key, inp in self.ext_inputs.items():
            setattr(s, key, inp.text())
        s.extras_folder_mode = self.extras_mode_combo.currentData()
        s.extras_folder_name = self.extras_name_input['edit'].text()
