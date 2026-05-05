from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from ui.v3.views.settings.base_tab import BaseSettingsTab

class ExtrasTab(BaseSettingsTab):
    def __init__(self, engine, parent=None):
        super().__init__(engine, parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QLabel("Extras Settings")
        header.setStyleSheet(Theme.get_page_header_style())
        layout.addWidget(header)
        layout.addSpacing(10)

        # --- Section: Types ---
        layout.addWidget(self._create_section_header("EXTRAS HANDLING"))
        
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
            lbl.setStyleSheet("font-weight: 600;")
            lbl.setFixedWidth(150)
            
            combo = QComboBox()
            combo.setFixedWidth(120)
            combo.addItems(["rename", "skip", "delete"])
            
            current_val = getattr(self.engine.config.settings, setting_key, "rename")
            idx = combo.findText(current_val)
            if idx >= 0: combo.setCurrentIndex(idx)
                
            self.extra_combos[setting_key] = combo
            
            tpl_input = QLineEdit(getattr(self.engine.config.settings, tpl_key, ""))
            tpl_input.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border: 1px solid {Theme.BORDER}; padding: 5px;")
            tpl_input.setEnabled(current_val == "rename")
            
            self.extra_templates[tpl_key] = tpl_input
            
            combo.currentTextChanged.connect(lambda text, t=tpl_input: t.setEnabled(text == "rename"))
            
            row.addWidget(lbl)
            row.addWidget(combo)
            row.addWidget(tpl_input)
            layout.addLayout(row)

        layout.addSpacing(15)
        layout.addWidget(Theme.create_hline())
        layout.addSpacing(10)

        # --- Section: Folder Placement ---
        layout.addWidget(self._create_section_header("EXTRAS FOLDER PLACEMENT"))
        
        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Folder Mode:")
        mode_lbl.setStyleSheet("font-weight: 600;")
        self.extras_mode_combo = QComboBox()
        self.extras_mode_combo.setFixedWidth(200)
        self.extras_mode_combo.addItem("Next to Parent (No extra folder)", "none")
        self.extras_mode_combo.addItem("Single 'Extras' folder", "single")
        self.extras_mode_combo.addItem("Categorized subfolders", "categorized")
        
        idx = self.extras_mode_combo.findData(self.engine.config.settings.extras_folder_mode)
        if idx >= 0: self.extras_mode_combo.setCurrentIndex(idx)
        
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.extras_mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)
        
        self.extras_name_input = self._create_input_group("Extras Folder Name", self.engine.config.settings.extras_folder_name, "Extras")
        layout.addLayout(self.extras_name_input['layout'])
        
        def update_name_state():
            self.extras_name_input['edit'].setEnabled(self.extras_mode_combo.currentData() == "single")
        
        self.extras_mode_combo.currentIndexChanged.connect(update_name_state)
        update_name_state()

        layout.addStretch()

    def save_to_settings(self, s):
        for key, combo in self.extra_combos.items():
            setattr(s, key, combo.currentText())
        for key, tpl in self.extra_templates.items():
            setattr(s, key, tpl.text())
        s.extras_folder_mode = self.extras_mode_combo.currentData()
        s.extras_folder_name = self.extras_name_input['edit'].text()
