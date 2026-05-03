from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout,
                             QPushButton, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from ui.v3.styles.theme import Theme

class InspectorPanel(QFrame):
    """Right-side panel for showing metadata details and resolving conflicts."""
    
    match_selected = Signal(int, dict) # file_id, media_item_data

    def __init__(self):
        super().__init__()
        self.setFixedWidth(340)
        self.setObjectName("Inspector")
        self.setStyleSheet(f"""
            QFrame#Inspector {{
                background-color: {Theme.SURFACE_DARK};
                border-left: 1px solid {Theme.BORDER};
            }}
            QLabel {{ color: {Theme.TEXT_MAIN}; }}
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 25, 20, 25)
        layout.setSpacing(18)

        # Poster Placeholder
        self.poster_label = QLabel("No Poster")
        self.poster_label.setFixedSize(300, 440)
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 12px; border: 1px solid {Theme.BORDER}; color: {Theme.TEXT_MUTED}; font-weight: 600;")
        layout.addWidget(self.poster_label)

        # Title & Year
        self.title_label = QLabel("Select a file")
        self.title_label.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.year_label = QLabel("")
        self.year_label.setStyleSheet(f"font-size: 15px; color: {Theme.PRIMARY}; font-weight: 700;")
        layout.addWidget(self.year_label)
        
        layout.addSpacing(5)
        layout.addWidget(Theme.create_hline())

        # Overview / Plot (Scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        self.plot_label = QLabel("")
        self.plot_label.setWordWrap(True)
        self.plot_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; line-height: 1.5; font-size: 13px;")
        self.plot_label.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.plot_label)
        layout.addWidget(scroll)

        # Technical Info Section
        self.tech_header = QLabel("TECHNICAL DETAILS")
        self.tech_header.setStyleSheet(f"font-weight: 800; font-size: 11px; color: {Theme.PRIMARY}; letter-spacing: 1.2px;")
        layout.addWidget(self.tech_header)

        self.tech_frame = QFrame()
        self.tech_frame.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 10px; border: 1px solid {Theme.BORDER};")
        self.tech_layout = QGridLayout(self.tech_frame)
        self.tech_layout.setContentsMargins(15, 15, 15, 15)
        self.tech_layout.setSpacing(10)
        
        # Pre-create labels for the grid
        self.labels = {}
        fields = [("RES", "Resolution"), ("CODEC", "Codec"), ("AUDIO", "Audio"), ("SIZE", "File Size")]
        for i, (key, label) in enumerate(fields):
            l1 = QLabel(label)
            l1.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-size: 10px; font-weight: 700; text-transform: uppercase; border: none;")
            l2 = QLabel("-")
            l2.setStyleSheet(f"color: {Theme.TEXT_MAIN}; font-size: 13px; font-weight: 600; border: none;")
            self.tech_layout.addWidget(l1, i, 0)
            self.tech_layout.addWidget(l2, i, 1)
            self.labels[key] = l2

        layout.addWidget(self.tech_frame)
        layout.addStretch()

    def set_empty(self):
        self.title_label.setText("Select a file")
        self.year_label.setText("")
        self.plot_label.setText("Select a file to see details and manage identification.")
        self.poster_label.setText("No Poster")
        for lbl in self.labels.values(): lbl.setText("-")

    def update_from_data(self, media_data, candidates=None):
        """Updates the panel with media information."""
        self.title_label.setText(media_data.get('title', 'Unknown'))
        self.year_label.setText(str(media_data.get('year', '')))
        self.plot_label.setText(media_data.get('overview', 'No description available.'))

    def update_tech_info(self, file_data):
        """Updates the technical details from file metadata."""
        if not file_data: return
        
        # Use database column 'resolution'
        self.labels['RES'].setText(file_data.get('resolution', '-'))
        
        self.labels['CODEC'].setText(file_data.get('video_codec', '-').upper())
        
        audio = file_data.get('audio_codec', '-')
        channels = file_data.get('audio_channels', '')
        audio_text = f"{audio.upper()} {channels}" if channels else audio.upper()
        self.labels['AUDIO'].setText(audio_text)
        
        # Use database column 'size_bytes'
        size_bytes = file_data.get('size_bytes', 0)
        size_gb = size_bytes / (1024*1024*1024)
        if size_gb >= 1:
            self.labels['SIZE'].setText(f"{size_gb:.2f} GB")
        else:
            self.labels['SIZE'].setText(f"{size_bytes/(1024*1024):.1f} MB")
