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

        # 1. Greeting & Title Header
        header_widget = QWidget()
        header_lay = QVBoxLayout(header_widget)
        header_lay.setContentsMargins(0, 0, 0, 0)
        header_lay.setSpacing(5)

        self.greeting_label = QLabel(self._get_greeting())
        self.greeting_label.setStyleSheet(f"letter-spacing: 1px; {Theme.get_h2_style()}")
        
        self.title_label = QLabel(T("dashboard.subtitle"))
        self.title_label.setStyleSheet(f"font-size: 32px; {Theme.get_h1_style()}")
        
        header_lay.addWidget(self.greeting_label)
        header_lay.addWidget(self.title_label)
        layout.addWidget(header_widget)
        layout.addSpacing(40)

        # 2. Main Content Area
        content_layout = QGridLayout()
        content_layout.setSpacing(30)

        # Scan Card (Primary Action)
        self.scan_card = self._create_action_card(
            "rocket",
            T("dashboard.scan.title"), 
            T("dashboard.scan.desc"),
            self.scan_clicked.emit
        )
        content_layout.addWidget(self.scan_card, 0, 0)
        
        # Stats Card
        self.stats_card = self._create_stats_card()
        content_layout.addWidget(self.stats_card, 0, 1)

        layout.addLayout(content_layout)
        layout.addStretch()

    def refresh_data(self):
        """Fetches latest stats from database and updates labels."""
        try:
            m_count = self.engine.db.media.get_count('movie')
            s_count = self.engine.db.media.get_count('tv')
        except:
            m_count, s_count = 0, 0
            
        self.movie_val.setText(str(m_count))
        self.movie_txt.setText(T("common.types.movie") if m_count == 1 else (T("common.types.movies") or "Movies"))
        
        self.show_val.setText(str(s_count))
        self.show_txt.setText(T("common.types.tv") if s_count == 1 else (T("common.types.tv_shows") or "TV Shows"))

    def refresh_style(self):
        """Updates the internal cards to use the new theme colors."""
        self.greeting_label.setStyleSheet(f"letter-spacing: 1px; {Theme.get_h2_style()}")
        self.title_label.setStyleSheet(f"font-size: 32px; {Theme.get_h1_style()}")
        
        # We don't need to recreate cards, just update the stylesheet of existing ones
        self.scan_card.setStyleSheet(f"""
            QFrame#ActionCard {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER};
                border-bottom: 4px solid {Theme.PRIMARY};
                border-radius: 16px;
            }}
            QFrame#ActionCard:hover {{
                background-color: {Theme.SURFACE_LIGHT};
                border-color: {Theme.PRIMARY};
            }}
        """)
        self.stats_card.setStyleSheet(f"""
            QFrame#StatsCard {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER};
                border-radius: 16px;
            }}
        """)
        # Refresh pixmaps in stat items would require more tracking, 
        # but the main colors are updated via setStyleSheet on the page.

    def _get_greeting(self):
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12: greeting = T("greeting.morning")
        elif 12 <= hour < 18: greeting = T("greeting.afternoon")
        elif 18 <= hour < 22: greeting = T("greeting.evening")
        else: greeting = T("greeting.night")

        user_name = self.engine.config.settings.user_name
        return f"{greeting}, {user_name}!" if user_name else f"{greeting},"

    def _create_action_card(self, icon, title, description, callback):
        card = QFrame()
        card.setObjectName("ActionCard")
        card.setStyleSheet(f"""
            QFrame#ActionCard {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER};
                border-bottom: 4px solid {Theme.PRIMARY};
                border-radius: 16px;
            }}
            QFrame#ActionCard:hover {{
                background-color: {Theme.SURFACE_LIGHT};
                border-color: {Theme.PRIMARY};
            }}
        """)
        card.setMinimumHeight(260)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(35, 35, 35, 35)
        layout.setSpacing(15)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(Theme.get_pixmap(icon, size=48, color=Theme.PRIMARY))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: 22px; {Theme.get_card_title_style()}")
        
        d_lbl = QLabel(description)
        d_lbl.setWordWrap(True)
        d_lbl.setStyleSheet(f"line-height: 1.4; {Theme.get_card_description_style()}")
        
        btn = QPushButton(T("dashboard.scan.button_text") or title)
        btn.setMinimumWidth(180)
        btn.setMinimumHeight(50)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(Theme.get_primary_button_style())
        btn.clicked.connect(callback)
        
        layout.addWidget(icon_lbl)
        layout.addWidget(t_lbl)
        layout.addWidget(d_lbl)
        layout.addStretch()
        layout.addWidget(btn)
        
        return card

    def _create_stats_card(self):
        card = QFrame()
        card.setObjectName("StatsCard")
        card.setStyleSheet(f"""
            QFrame#StatsCard {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER};
                border-radius: 16px;
            }}
        """)
        card.setMinimumHeight(260)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(35, 35, 35, 35)
        
        t_lbl = QLabel(T("dashboard.stats.overview_title") or "Workspace Overview")
        t_lbl.setStyleSheet(f"font-size: 18px; margin-bottom: 20px; {Theme.get_card_title_style()}")
        layout.addWidget(t_lbl)

        # Stats Grid
        stats_grid = QHBoxLayout()
        stats_grid.setSpacing(30)
        
        try:
            m_count = self.engine.db.media.get_count('movie')
            s_count = self.engine.db.media.get_count('tv')
        except:
            m_count, s_count = 0, 0

        # Movies
        m_lay, self.movie_val, self.movie_txt = self._create_stat_item("movie", m_count, T("common.types.movie") if m_count == 1 else (T("common.types.movies") or "Movies"))
        stats_grid.addLayout(m_lay)
        
        # Shows
        s_lay, self.show_val, self.show_txt = self._create_stat_item("tv", s_count, T("common.types.tv") if s_count == 1 else (T("common.types.tv_shows") or "TV Shows"))
        stats_grid.addLayout(s_lay)
        
        stats_grid.addStretch()
        
        layout.addLayout(stats_grid)
        layout.addStretch()
        
        return card

    def _create_stat_item(self, icon, value, label):
        lay = QVBoxLayout()
        lay.setSpacing(5)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(Theme.get_pixmap(icon, size=32, color=Theme.TEXT_MUTED))
        icon_lbl.setStyleSheet("margin-bottom: 5px; border: none; background: transparent;")
        
        val_lbl = QLabel(str(value))
        val_lbl.setStyleSheet(Theme.get_stat_value_style())
        
        txt_lbl = QLabel(label)
        txt_lbl.setStyleSheet(f"text-transform: uppercase; letter-spacing: 1px; {Theme.get_hint_style()}")
        
        lay.addWidget(icon_lbl)
        lay.addWidget(val_lbl)
        lay.addWidget(txt_lbl)
        return lay, val_lbl, txt_lbl
