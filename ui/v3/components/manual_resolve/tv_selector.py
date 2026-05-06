from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox, QSpinBox
from PySide6.QtCore import Qt, Signal, QEvent
from core.i18n import T

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

        # 1. Season/Episode Fields (The type is now managed by the main search)
        self.tv_container = QWidget()
        tv_layout = QHBoxLayout(self.tv_container)
        tv_layout.setContentsMargins(0, 0, 0, 0)
        tv_layout.setSpacing(10)

        tv_layout.addWidget(QLabel("S:"))
        self.season_spin = self._create_spin(0, 999, T("common.none"))
        tv_layout.addWidget(self.season_spin)

        tv_layout.addWidget(QLabel("E:"))
        self.episode_spin = self._create_spin(0, 999, T("common.none"))
        tv_layout.addWidget(self.episode_spin)

        layout.addWidget(self.tv_container)
        
        # Initial visibility: Hide TV fields by default
        self.tv_container.setVisible(False)
        
        layout.addStretch()

    def _create_spin(self, min_v, max_v, special_text):
        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setSpecialValueText(special_text)
        spin.setFixedWidth(70)
        spin.lineEdit().installEventFilter(self)
        return spin

    def set_values(self, s=0, e=0):
        self.season_spin.setValue(int(s) if s else 0)
        self.episode_spin.setValue(int(e) if e else 0)

    def get_values(self):
        return {
            'season': self.season_spin.value(),
            'episode': self.episode_spin.value()
        }
