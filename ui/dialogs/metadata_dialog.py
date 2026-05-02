import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QFrame
from PySide6.QtCore import Qt

class MetadataDialog(QDialog):
    def __init__(self, parent, file_path, meta):
        super().__init__(parent)
        self.setWindowTitle("Metadata Transparency")
        self.setMinimumSize(550, 650)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { color: #0f172a; }
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { border: none; background: #f8fafc; width: 8px; }
            QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 4px; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Header
        header_layout = QVBoxLayout()
        title = QLabel("Metadata Transparency")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0078d4;")
        header_layout.addWidget(title)
        
        file_name = QLabel(os.path.basename(file_path))
        file_name.setStyleSheet("font-size: 13px; color: #64748b; font-weight: 500;")
        header_layout.addWidget(file_name)
        
        # Separator line
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #cbd5e1;")
        header_layout.addWidget(sep)
        layout.addLayout(header_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll_layout = QVBoxLayout(content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)
        
        # --- API DATA ---
        api_group = self._create_section("🌍 API MATCH (ENRICHED DATA)")
        if meta and meta.get('details'):
            d = meta['details']
            self._add_metadata_rows(api_group.layout(), d)
        else:
            api_group.layout().addWidget(QLabel("No API matches found yet. Run Unified Analysis first."))
        scroll_layout.addWidget(api_group)
        
        # --- GUESSIT DATA ---
        guess_group = self._create_section("🔍 FILENAME PARSE (GUESSIT)")
        if meta and meta.get('extras'):
            e = meta['extras']
            data = e.to_template_dict() if hasattr(e, 'to_template_dict') else e
            self._add_metadata_rows(guess_group.layout(), data)
        else:
             guess_group.layout().addWidget(QLabel("No parser data available."))
        scroll_layout.addWidget(guess_group)

        # --- TECHNICAL DATA ---
        tech_group = self._create_section("⚙️ TECHNICAL SPECS (MEDIINFO/PROBE)")
        from metadata.video_metadata import get_video_metadata
        tech = get_video_metadata(file_path)
        self._add_metadata_rows(tech_group.layout(), tech)
        scroll_layout.addWidget(tech_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Bottom Button
        actions = QHBoxLayout()
        actions.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedSize(100, 35)
        close_btn.setStyleSheet("""
            QPushButton { 
                background-color: #0078d4; color: white; border-radius: 6px; 
                font-weight: 700; border: none;
            }
            QPushButton:hover { background-color: #005a9e; }
        """)
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)
        layout.addLayout(actions)

    def _create_section(self, title):
        frame = QFrame()
        frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 10px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 10px; font-weight: 800; color: #64748b; letter-spacing: 1px; margin-bottom: 5px;")
        layout.addWidget(lbl)
        return frame

    def _add_metadata_rows(self, layout, data):
        for k, v in data.items():
            if v and v != "Unknown" and not isinstance(v, (list, dict)):
                row = QWidget()
                r_layout = QHBoxLayout(row)
                r_layout.setContentsMargins(0, 0, 0, 0)
                
                key_lbl = QLabel(f"{str(k).replace('_', ' ').title()}:")
                key_lbl.setStyleSheet("font-weight: 600; color: #334155; font-size: 12px;")
                
                val_lbl = QLabel(str(v))
                val_lbl.setStyleSheet("color: #0f172a; font-size: 12px;")
                val_lbl.setWordWrap(True)
                
                r_layout.addWidget(key_lbl, 1)
                r_layout.addWidget(val_lbl, 2)
                layout.addWidget(row)
