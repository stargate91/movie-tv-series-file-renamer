import os
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QCheckBox
from PySide6.QtCore import Qt, Signal
from ui.components.image_widgets import ImageLoader

class MovieCard(QFrame):
    selection_changed = Signal(bool) # Signal to notify MainWindow
    
    def __init__(self, file_path, meta, on_edit, on_remove=None):
        super().__init__()
        self.setObjectName("Card")
        self.setMinimumHeight(80)
        self.file_path = file_path
        self.meta = meta
        
        status = meta['status'] if meta else 'pending'
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 15, 10)
        
        # Checkbox for multi-select
        self.checkbox = QCheckBox()
        self.checkbox.setFixedWidth(30)
        self.checkbox.stateChanged.connect(lambda state: self.selection_changed.emit(state == Qt.Checked.value))
        layout.addWidget(self.checkbox, 0, Qt.AlignVCenter)
        
        # Status Icon/Indicator
        is_manual = meta.get('is_manual', False) if meta else False
        
        if is_manual:
            color = "#6366f1" # Indigo for manual
        else:
            color = "#3fb950" if status == 'one_match' else "#d29922" if status == 'multiple_matches' else "#f85149" if status == 'no_match' else "#8b949e"
        
        indicator = QFrame()
        indicator.setFixedSize(12, 12)
        indicator.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        layout.addWidget(indicator, 0, Qt.AlignVCenter)
        
        # Poster
        poster_url = None
        is_episode = meta.get('file_type') == 'episode' if meta else False
        
        if meta and status == 'one_match':
            p_path = meta.get('details', {}).get('poster_path') or meta.get('details', {}).get('still_path')
            if p_path:
                poster_url = f"https://image.tmdb.org/t/p/w200{p_path}"
        
        # Use wider loader for episodes (horizontal stills)
        width = 100 if is_episode else 40
        self.poster = ImageLoader(poster_url, width=width, height=60)
        layout.addWidget(self.poster, 0, Qt.AlignVCenter)
        
        # Text Info
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignVCenter)
        if meta and status == 'one_match':
            d = meta.get('details', {})
            title_text = f"{d.get('title') or d.get('name')}"
            year_val = (d.get('release_date') or d.get('first_air_date', ''))[:4]
            if year_val: title_text += f" ({year_val})"
            
            title_lbl = QLabel(title_text)
            title_lbl.setStyleSheet("font-weight: bold; font-size: 15px; color: #111827;")
            
            if is_episode and d.get('air_date'):
                air_lbl = QLabel(f"Aired: {d.get('air_date')}")
                air_lbl.setStyleSheet("font-size: 10px; color: #6b7280; margin-top: -2px;")
                info_layout.addWidget(title_lbl)
                info_layout.addWidget(air_lbl)
            else:
                info_layout.addWidget(title_lbl)
        
        elif meta and status == 'multiple_matches':
            guessed = meta.get('extras', {}).get('title', 'Unknown')
            title_lbl = QLabel(f"{guessed} (Multiple Matches)")
            title_lbl.setStyleSheet("font-weight: bold; font-size: 15px; color: #b45309;")
            info_layout.addWidget(title_lbl)
        else:
            title_lbl = QLabel(os.path.basename(file_path))
            title_lbl.setStyleSheet("font-weight: bold; font-size: 15px; color: #111827;")
            info_layout.addWidget(title_lbl)
            
        file_lbl = QLabel(os.path.basename(file_path))
        file_lbl.setStyleSheet("font-size: 11px; color: #6b7280;")
        info_layout.addWidget(file_lbl)
        
        layout.addLayout(info_layout, 1)
        
        # Store callbacks
        self.on_edit_cb = on_edit
        self.on_remove_cb = on_remove

        # Info Button
        self.info_btn = QPushButton("ⓘ")
        self.info_btn.setFixedSize(40, 40)
        self.info_btn.setStyleSheet("font-size: 18px; color: #6b7280; border: none; background: transparent;")
        self.info_btn.setToolTip("Show Variables")
        self.info_btn.clicked.connect(self.show_metadata)
        layout.addWidget(self.info_btn, 0, Qt.AlignVCenter)

        # Edit Button
        self.edit_btn = QPushButton("✎")
        self.edit_btn.setFixedSize(50, 50)
        self.edit_btn.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.edit_btn.clicked.connect(lambda: self.on_edit_cb(None))
        layout.addWidget(self.edit_btn, 0, Qt.AlignVCenter)

        # Remove Button
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(40, 40)
        self.remove_btn.setStyleSheet("font-size: 18px; color: #f85149; border: none; background: transparent;")
        self.remove_btn.setToolTip("Remove from list")
        if self.on_remove_cb:
            self.remove_btn.clicked.connect(lambda: self.on_remove_cb(None))
        layout.addWidget(self.remove_btn, 0, Qt.AlignVCenter)

    def show_metadata(self):
        dialog = MetadataDialog(self, self.file_path, self.meta)
        dialog.exec()

    def mouseDoubleClickEvent(self, event):
        if self.on_edit_cb:
            self.on_edit_cb(None)
