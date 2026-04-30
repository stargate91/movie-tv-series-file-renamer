import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QFrame
from PySide6.QtCore import Qt

class MetadataDialog(QDialog):
    def __init__(self, parent, file_path, meta):
        super().__init__(parent)
        self.setWindowTitle("Metadata Transparency")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel(f"File: {os.path.basename(file_path)}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll_layout = QVBoxLayout(content)
        
        # --- API DATA ---
        api_group = self._create_section("🌍 API Metadata (TMDB/OMDB)")
        if meta and meta.get('details'):
            d = meta['details']
            for k, v in d.items():
                if isinstance(v, (str, int, float)) and v:
                    api_group.layout().addWidget(QLabel(f"<b>{k}:</b> {v}"))
        else:
            api_group.layout().addWidget(QLabel("No API metadata found."))
        scroll_layout.addWidget(api_group)
        
        # --- GUESSIT DATA ---
        guess_group = self._create_section("🔍 Guessit Metadata (Filename Parse)")
        if meta and meta.get('extras'):
            e = meta['extras']
            # If it's the ExtraMetadata object, use to_template_dict
            data = e.to_template_dict() if hasattr(e, 'to_template_dict') else e
            for k, v in data.items():
                if v and v != "Unknown":
                    guess_group.layout().addWidget(QLabel(f"<b>{k}:</b> {v}"))
        scroll_layout.addWidget(guess_group)

        # --- TECHNICAL DATA ---
        tech_group = self._create_section("⚙️ Technical Metadata (FFmpeg Probe)")
        from metadata.video_metadata import get_video_metadata
        tech = get_video_metadata(file_path)
        for k, v in tech.items():
            if v:
                tech_group.layout().addWidget(QLabel(f"<b>{k}:</b> {v}"))
        scroll_layout.addWidget(tech_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _create_section(self, title):
        frame = QFrame()
        frame.setStyleSheet("background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 10px;")
        layout = QVBoxLayout(frame)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: bold; color: #374151; margin-bottom: 5px;")
        layout.addWidget(lbl)
        return frame
