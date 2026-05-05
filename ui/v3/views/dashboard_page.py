import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QGridLayout
from PySide6.QtCore import Qt, Signal
from ui.v3.styles.theme import Theme
from core.i18n import T

class DashboardPage(QWidget):
    """
    Main landing page of the application.
    Displays a greeting and quick access to major actions.
    """
    scan_clicked = Signal()

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # 1. Greeting Header
        self.greeting_label = QLabel(self._get_greeting())
        self.greeting_label.setStyleSheet(Theme.get_h2_style())
        
        self.title_label = QLabel(T("dashboard.subtitle"))
        self.title_label.setStyleSheet(Theme.get_h1_style())
        
        layout.addWidget(self.greeting_label)
        layout.addWidget(self.title_label)
        layout.addSpacing(30)

        # 2. Main Action Card
        action_layout = QHBoxLayout()
        action_layout.setSpacing(20)

        self.scan_card = self._create_action_card(
            T("dashboard.scan.title"), 
            T("dashboard.scan.desc"),
            self.scan_clicked.emit
        )
        action_layout.addWidget(self.scan_card)
        
        # Add a placeholder for a second card (e.g. "Library Stats")
        self.stats_card = self._create_stats_card()
        action_layout.addWidget(self.stats_card)

        layout.addLayout(action_layout)
        layout.addStretch()

    def _get_greeting(self):
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12: greeting = T("greeting.morning")
        elif 12 <= hour < 18: greeting = T("greeting.afternoon")
        elif 18 <= hour < 22: greeting = T("greeting.evening")
        else: greeting = T("greeting.night")

        user_name = self.engine.config.settings.user_name
        return f"{greeting}, {user_name}!" if user_name else f"{greeting},"

    def _create_action_card(self, title, description, callback):
        card = QFrame()
        card.setStyleSheet(Theme.get_card_style())
        card.setFixedHeight(220)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignLeft)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        
        d_lbl = QLabel(description)
        d_lbl.setWordWrap(True)
        d_lbl.setStyleSheet("color: #aaa; margin-bottom: 20px;")
        
        btn = QPushButton(title)
        btn.setFixedSize(160, 45)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        
        layout.addWidget(t_lbl)
        layout.addWidget(d_lbl)
        layout.addStretch()
        layout.addWidget(btn)
        
        return card

    def _create_stats_card(self):
        card = QFrame()
        card.setStyleSheet(Theme.get_card_style())
        card.setFixedHeight(220)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)
        
        t_lbl = QLabel(T("dashboard.stats.overview_title"))
        t_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        
        # Example stats (would be dynamic in a real scenario)
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(5)
        
        # We can try to get real counts from DB repositories
        try:
            m_count = self.engine.db.media.get_count('movie')
            s_count = self.engine.db.media.get_count('tv')
        except:
            m_count, s_count = 0, 0

        m_lbl = QLabel(T("dashboard.stats.movies_indexed", count=m_count))
        s_lbl = QLabel(T("dashboard.stats.series_indexed", count=s_count))
        m_lbl.setStyleSheet("color: #888;")
        s_lbl.setStyleSheet("color: #888;")
        
        layout.addWidget(t_lbl)
        layout.addSpacing(15)
        layout.addWidget(m_lbl)
        layout.addWidget(s_lbl)
        layout.addStretch()
        
        return card
