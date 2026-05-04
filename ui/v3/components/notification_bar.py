from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal
from ui.v3.styles.theme import Theme

class NotificationBar(QWidget):
    undo_requested = Signal(str) # batch_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.batch_id = None
        self._init_ui()
        self.hide()

    def _init_ui(self):
        # Premium dark glass look
        self.setFixedHeight(50)
        self.setFixedWidth(500)
        self.setStyleSheet(f"""
            QWidget#NotifContainer {{
                background-color: {Theme.SURFACE_DARK}ee;
                border: 1px solid {Theme.PRIMARY};
                border-radius: 25px;
            }}
            QLabel {{
                color: {Theme.TEXT_MAIN};
                font-weight: 600;
                font-size: 13px;
                border: none;
                background: transparent;
            }}
        """)
        
        container = QWidget(self)
        container.setObjectName("NotifContainer")
        container.setFixedSize(500, 50)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(20, 0, 10, 0)
        layout.setSpacing(15)

        self.label = QLabel("Operation successful")
        
        self.undo_btn = QPushButton("UNDO")
        self.undo_btn.setFixedSize(80, 30)
        self.undo_btn.setCursor(Qt.PointingHandCursor)
        self.undo_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.PRIMARY};
                color: white;
                border-radius: 15px;
                font-weight: 800;
                font-size: 11px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {Theme.PRIMARY_HOVER};
            }}
        """)
        self.undo_btn.clicked.connect(self._on_undo_clicked)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(f"color: {Theme.TEXT_MUTED}; border: none; font-size: 16px; background: transparent;")
        close_btn.clicked.connect(self.hide_notification)

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.undo_btn)
        layout.addWidget(close_btn)

        # Effects
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_notification)

    def show_message(self, message, batch_id=None, duration=8000):
        self.label.setText(message)
        self.batch_id = batch_id
        self.undo_btn.setVisible(batch_id is not None)
        
        # Position at bottom center of parent
        if self.parent():
            p_rect = self.parent().rect()
            x = (p_rect.width() - self.width()) // 2
            y = p_rect.height() - 80
            self.move(x, y)

        self.show()
        self.raise_()
        
        # Fade in animation
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()
        
        self.timer.start(duration)

    def hide_notification(self):
        # Fade out animation
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.InCubic)
        self.anim.finished.connect(self.hide)
        self.anim.start()

    def _on_undo_clicked(self):
        if self.batch_id:
            self.undo_requested.emit(self.batch_id)
            self.hide_notification()
