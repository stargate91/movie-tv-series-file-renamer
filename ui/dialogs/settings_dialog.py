from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QCheckBox, QComboBox, QFormLayout, QTabWidget, QWidget

class SettingsDialog(QDialog):
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.cfg = config_manager
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 450)
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # --- API Tab ---
        api_tab = QWidget()
        api_layout = QFormLayout(api_tab)
        self.omdb_input = QLineEdit(self.cfg.settings.omdb_key)
        self.tmdb_input = QLineEdit(self.cfg.settings.tmdb_key)
        self.tmdb_token = QLineEdit(self.cfg.settings.tmdb_bearer_token)
        
        api_layout.addRow("OMDB API Key:", self.omdb_input)
        api_layout.addRow("TMDB API Key:", self.tmdb_input)
        api_layout.addRow("TMDB Bearer Token:", self.tmdb_token)
        self.tabs.addTab(api_tab, "API Keys")
        
        # --- Format Tab ---
        format_tab = QWidget()
        format_layout = QFormLayout(format_tab)
        
        self.case_combo = QComboBox()
        self.case_combo.addItems(["none", "lower", "upper", "title"])
        self.case_combo.setCurrentText(self.cfg.settings.filename_case)
        
        self.sep_combo = QComboBox()
        self.sep_combo.addItems(["space", "dot", "dash", "underscore"])
        self.sep_combo.setCurrentText(self.cfg.settings.separator)
        
        self.padding_check = QCheckBox("Use Zero Padding (S01E01)")
        self.padding_check.setChecked(self.cfg.settings.zero_padding)
        
        self.posters_check = QCheckBox("Download posters to folder (poster.jpg)")
        self.posters_check.setChecked(self.cfg.settings.download_posters)
        
        format_layout.addRow("Filename Case:", self.case_combo)
        format_layout.addRow("Separator:", self.sep_combo)
        format_layout.addRow(self.padding_check)
        format_layout.addRow(self.posters_check)
        self.tabs.addTab(format_tab, "Formatting")
        
        # --- Renaming Tab ---
        rename_tab = QWidget()
        rename_layout = QFormLayout(rename_tab)
        
        self.movie_tmpl = QLineEdit(self.cfg.settings.movie_template)
        self.tv_tmpl = QLineEdit(self.cfg.settings.episode_template)
        self.custom_input = QLineEdit(self.cfg.settings.custom_variable)
        
        rename_layout.addRow("Movie Template:", self.movie_tmpl)
        rename_layout.addRow("TV Template:", self.tv_tmpl)
        rename_layout.addRow("Custom Variable:", self.custom_input)
        
        self.tabs.addTab(rename_tab, "Templates")
        
        layout.addWidget(self.tabs)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def save(self):
        self.cfg.settings.omdb_key = self.omdb_input.text()
        self.cfg.settings.tmdb_key = self.tmdb_input.text()
        self.cfg.settings.tmdb_bearer_token = self.tmdb_token.text()
        
        self.cfg.settings.filename_case = self.case_combo.currentText()
        self.cfg.settings.separator = self.sep_combo.currentText()
        self.cfg.settings.zero_padding = self.padding_check.isChecked()
        self.cfg.settings.download_posters = self.posters_check.isChecked()
        self.cfg.settings.movie_template = self.movie_tmpl.text()
        self.cfg.settings.episode_template = self.tv_tmpl.text()
        self.cfg.settings.custom_variable = self.custom_input.text()
        
        self.cfg.save()
        self.accept()
