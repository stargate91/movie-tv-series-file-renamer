from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpinBox, QComboBox
from PySide6.QtCore import Qt, Signal, QEvent

class TVMetadataSelector(QWidget):
    """
    UI component for selecting TV Show specific metadata (Type, Season, Episode).
    """
    type_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 1. Type Toggle
        layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Movie", "TV Show"])
        self.type_combo.setFixedWidth(110)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)

        # 2. Season/Episode Fields
        self.tv_container = QWidget()
        tv_layout = QHBoxLayout(self.tv_container)
        tv_layout.setContentsMargins(0, 0, 0, 0)
        tv_layout.setSpacing(10)

        tv_layout.addWidget(QLabel("S:"))
        self.season_spin = self._create_spin(0, 999, "None")
        tv_layout.addWidget(self.season_spin)

        tv_layout.addWidget(QLabel("E:"))
        self.episode_spin = self._create_spin(0, 999, "None")
        tv_layout.addWidget(self.episode_spin)

        layout.addWidget(self.tv_container)
        layout.addStretch()

    def _create_spin(self, min_v, max_v, special_text):
        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setSpecialValueText(special_text)
        spin.setFixedWidth(70)
        spin.lineEdit().installEventFilter(self)
        return spin

    def _on_type_changed(self, text):
        self.tv_container.setVisible(text == "TV Show")
        self.type_changed.emit(text)

    def eventFilter(self, source, event):
        """Auto-reset to 0 if field is cleared manually."""
        if event.type() == QEvent.FocusOut:
            if not source.text().strip():
                if source == self.season_spin.lineEdit(): self.season_spin.setValue(0)
                if source == self.episode_spin.lineEdit(): self.episode_spin.setValue(0)
        return super().eventFilter(source, event)

    def set_values(self, m_type, s=0, e=0):
        self.type_combo.setCurrentText("TV Show" if m_type == "tv" else "Movie")
        self.season_spin.setValue(int(s) if s else 0)
        self.episode_spin.setValue(int(e) if e else 0)

    def get_values(self):
        return {
            'type': 'tv' if self.type_combo.currentText() == "TV Show" else 'movie',
            'season': self.season_spin.value(),
            'episode': self.episode_spin.value()
        }
