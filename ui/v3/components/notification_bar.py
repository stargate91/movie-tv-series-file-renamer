from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal
from ui.v3.styles.theme import Theme
from core.i18n import T

class NotificationBar(QWidget):
    undo_requested = Signal(str) # batch_id
    action_requested = Signal(object) # custom payload

    def __init__(self, parent=None):
        super().__init__(parent)
        self.batch_id = None
        self.custom_payload = None
        self.is_custom = False
        
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        if parent:
            parent.installEventFilter(self)
            
        self._init_ui()
        self.hide()

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == event.Type.Resize:
            self.resize(obj.size())
            self._center_container()
        return super().eventFilter(obj, event)

    def _center_container(self, scale=1.0):
        if not hasattr(self, 'container'): return
        base_w, base_h = 560, 70
        w = int(base_w * scale)
        h = int(base_h * scale)
        self.container.setFixedSize(w, h)
        x = (self.width() - w) // 2
        y = (self.height() - h) // 2
        self.container.move(x, y)

    def paintEvent(self, event):
        """Draws a softer, slate-tinted dimming background."""
        from PySide6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # slate-900 tint with lower alpha for less 'aggression'
        painter.fillRect(self.rect(), QColor(15, 23, 42, 110))

    def mousePressEvent(self, event):
        if hasattr(self, 'container') and not self.container.geometry().contains(event.pos()):
            self.hide_notification()
            
    def _init_ui(self):
        # The Pill Container
        self.container = QWidget(self)
        self.container.setObjectName("NotifContainer")
        self.container.setFixedSize(560, 70)
        
        # Premium Glassmorphism + Primary Glow
        self.container.setStyleSheet(f"""
            QWidget#NotifContainer {{
                background-color: #1E293B;
                border: 1px solid {Theme.PRIMARY};
                border-radius: 20px;
            }}
        """)
        
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(25, 0, 20, 0)
        layout.setSpacing(15)

        self.label = QLabel(T("common.operation_successful") if T("common.operation_successful") != "common.operation_successful" else "Operation successful")
        self.label.setStyleSheet("background: transparent; color: #F1F5F9; font-weight: 600; font-size: 14px;")
        
        self.undo_btn = QPushButton(T("common.undo") if T("common.undo") != "common.undo" else "Undo")
        self.undo_btn.setMinimumWidth(110)
        self.undo_btn.setFixedHeight(38)
        self.undo_btn.setCursor(Qt.PointingHandCursor)
        self.undo_btn.setStyleSheet(Theme.get_notification_undo_style())
        self.undo_btn.clicked.connect(self._on_undo_clicked)

        close_btn = QPushButton()
        close_btn.setIcon(Theme.get_icon("x", size=18, color="#94A3B8"))
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; border-radius: 16px; } QPushButton:hover { background: rgba(255,255,255,0.1); }")
        close_btn.clicked.connect(self.hide_notification)

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.undo_btn)
        layout.addWidget(close_btn)

        # Opacity Effect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_notification)

    def show_message(self, message, batch_id=None, duration=8000):
        self.is_custom = False
        self.label.setText(message)
        self.batch_id = batch_id
        self.undo_btn.setText(T("common.undo") if T("common.undo") != "common.undo" else "Undo")
        self.undo_btn.setVisible(batch_id is not None)
        self._show_animated(duration)

    def show_custom_action(self, message, button_text, payload=None, duration=15000):
        self.is_custom = True
        self.label.setText(message)
        self.custom_payload = payload
        self.undo_btn.setText(button_text)
        self.undo_btn.setVisible(True)
        self._show_animated(duration)
        
    def _show_animated(self, duration):
        if self.parent():
            self.resize(self.parent().size())
            self._center_container(0.95) # Start slightly smaller

        self.show()
        self.raise_()
        
        # 1. Opacity Animation
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(400)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_anim.start()
        
        # 2. Scale (Geometry) Animation for a 'pop' effect
        from PySide6.QtCore import QVariantAnimation
        self.scale_anim = QVariantAnimation(self)
        self.scale_anim.setDuration(400)
        self.scale_anim.setStartValue(0.95)
        self.scale_anim.setEndValue(1.0)
        self.scale_anim.setEasingCurve(QEasingCurve.OutBack)
        self.scale_anim.valueChanged.connect(self._center_container)
        self.scale_anim.start()
        
        self.timer.start(duration)

    def hide_notification(self):
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.InCubic)
        self.fade_anim.finished.connect(self.hide)
        self.fade_anim.start()

    def _on_undo_clicked(self):
        if self.is_custom:
            self.action_requested.emit(self.custom_payload)
            self.hide_notification()
        elif self.batch_id:
            self.undo_requested.emit(self.batch_id)
            self.hide_notification()
