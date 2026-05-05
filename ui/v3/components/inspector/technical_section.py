from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme

class TechnicalSection(QWidget):
    """
    Compact section for displaying technical file information (Resolution, Codecs, Size).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QLabel("TECHNICAL")
        header.setStyleSheet(f"font-weight: 800; font-size: 10px; color: {Theme.TEXT_DIM}; letter-spacing: 1.5px;")
        layout.addWidget(header)

        self.frame = QFrame()
        self.frame.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 10px; border: 1px solid {Theme.BORDER};")
        grid = QGridLayout(self.frame)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setSpacing(6)
        grid.setColumnStretch(1, 1)

        self.labels = {}
        fields = [("RES", "RES"), ("CODEC", "CODEC"), ("AUDIO", "AUDIO"), ("SIZE", "SIZE")]
        for i, (key, label) in enumerate(fields):
            l_key = QLabel(label)
            l_key.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-size: 9px; font-weight: 800; letter-spacing: 1px; border: none;")
            l_val = QLabel("-")
            l_val.setStyleSheet(f"color: {Theme.TEXT_MAIN}; font-size: 12px; font-weight: 600; border: none;")
            grid.addWidget(l_key, i, 0)
            grid.addWidget(l_val, i, 1)
            self.labels[key] = l_val

        layout.addWidget(self.frame)

    def update_info(self, file_data):
        if not file_data:
            self.clear()
            return

        self.labels['RES'].setText(str(file_data.get('resolution') or '-'))
        self.labels['CODEC'].setText(str(file_data.get('video_codec') or '-').upper())
        
        audio = str(file_data.get('audio_codec') or '-').upper()
        channels = str(file_data.get('audio_channels') or '')
        self.labels['AUDIO'].setText(f"{audio} {channels}".strip())

        size_bytes = file_data.get('size_bytes', 0)
        size_gb = size_bytes / (1024**3)
        if size_gb >= 1:
            self.labels['SIZE'].setText(f"{size_gb:.2f} GB")
        else:
            self.labels['SIZE'].setText(f"{size_bytes/(1024**2):.1f} MB")

    def clear(self):
        for lbl in self.labels.values():
            lbl.setText("-")
