from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt
from ui.components.image_widgets import ImageLoader

class SeriesHeader(QFrame):
    def __init__(self, title, poster_path, on_edit=None):
        super().__init__()
        self.setStyleSheet("background-color: #f3f4f6; border-radius: 12px; margin-top: 20px; border: 1px solid #e5e7eb;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Series Poster (Large)
        url = f"https://image.tmdb.org/t/p/w200{poster_path}" if poster_path else None
        self.poster = ImageLoader(url, 70, 105)
        # Add padding to prevent clipping
        self.poster.setStyleSheet("padding: 2px; background: transparent; border: none;")
        layout.addWidget(self.poster)
        
        # Text
        info = QVBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #111827; background: transparent; border: none;")
        info.addWidget(title_lbl)
        
        subtitle = QLabel("TV SERIES")
        subtitle.setStyleSheet("font-size: 10px; font-weight: bold; color: #6b7280; letter-spacing: 2px; background: transparent; border: none;")
        info.addWidget(subtitle)
        layout.addLayout(info)
        
        layout.addStretch()
        
        # Action Button
        if on_edit:
            self.btn = QPushButton("🪄 Fix Whole Series")
            self.btn.setCursor(Qt.PointingHandCursor)
            self.btn.setStyleSheet("""
                QPushButton {
                    background: #6366f1; color: white; border: none; 
                    padding: 8px 15px; border-radius: 6px; font-weight: bold;
                }
                QPushButton:hover { background: #4f46e5; }
            """)
            self.btn.clicked.connect(on_edit)
            layout.addWidget(self.btn)

class SeasonHeader(QWidget):
    def __init__(self, season_num, poster_path=None, year_range="", on_edit=None):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 10, 10, 5) # Indented from series
        
        # Larger Season Poster
        url = f"https://image.tmdb.org/t/p/w200{poster_path}" if poster_path else None
        self.poster = ImageLoader(url, 40, 60)
        # Add a small padding around the poster to prevent clipping
        self.poster.setStyleSheet("padding: 2px;") 
        layout.addWidget(self.poster)
        
        # Clean year_range from existing brackets if any
        clean_year = year_range.strip("() ")
        
        info = QVBoxLayout()
        lbl = QLabel(f"Season {season_num} <span style='color: #6b7280; font-weight: normal; font-size: 13px;'>({clean_year})</span>" if clean_year else f"Season {season_num}")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #374151; background: transparent; border: none;")
        info.addWidget(lbl)
        
        # Decorative blue line under the title
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #3b82f6; min-height: 2px; max-height: 2px; border: none; margin-right: 20px;")
        info.addWidget(line)
        layout.addLayout(info)
        
        layout.addStretch()
        
        if on_edit:
            self.btn = QPushButton("✎ Fix Season")
            self.btn.setCursor(Qt.PointingHandCursor)
            self.btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #3b82f6; border: 1px solid #3b82f6; 
                    padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: bold;
                }
                QPushButton:hover { background: #eff6ff; }
            """)
            self.btn.clicked.connect(on_edit)
            layout.addWidget(self.btn)
