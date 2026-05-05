from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme

class MediaSection(QWidget):
    """
    Main section for media metadata (Title, Year, Overview, Episode info).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. Title & Status Row
        title_row = QHBoxLayout()
        self.title_lbl = QLabel("Select a file")
        self.title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {Theme.TEXT_MAIN};")
        self.title_lbl.setWordWrap(True)
        title_row.addWidget(self.title_lbl)
        layout.addLayout(title_row)

        # 2. Year & Status Badge
        sub_row = QHBoxLayout()
        self.year_lbl = QLabel("")
        self.year_lbl.setStyleSheet(f"font-size: 15px; color: {Theme.PRIMARY}; font-weight: 700;")
        sub_row.addWidget(self.year_lbl)
        
        self.status_badge = QLabel("")
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.hide()
        sub_row.addStretch()
        sub_row.addWidget(self.status_badge)
        layout.addLayout(sub_row)

        # 3. Episode Frame (TV specific)
        self.ep_frame = QFrame()
        self.ep_frame.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 10px; border: 1px solid {Theme.BORDER};")
        ep_layout = QVBoxLayout(self.ep_frame)
        ep_layout.setContentsMargins(14, 12, 14, 12)
        ep_layout.setSpacing(4)

        self.ep_id_lbl = QLabel("")
        self.ep_id_lbl.setStyleSheet(f"font-size: 13px; color: {Theme.PRIMARY}; font-weight: 700; border: none;")
        self.ep_title_lbl = QLabel("")
        self.ep_title_lbl.setWordWrap(True)
        self.ep_title_lbl.setStyleSheet(f"font-size: 14px; color: {Theme.TEXT_MAIN}; font-weight: 600; border: none;")
        
        ep_layout.addWidget(self.ep_id_lbl)
        ep_layout.addWidget(self.ep_title_lbl)
        self.ep_frame.hide()
        layout.addWidget(self.ep_frame)

        # 4. Overview
        self.overview_lbl = QLabel("Select a file to see details and manage identification.")
        self.overview_lbl.setWordWrap(True)
        self.overview_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED}; line-height: 1.5; font-size: 12px;")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(self.overview_lbl)
        layout.addWidget(scroll, 1)

    def update_media(self, data):
        if not data: return
        self.title_lbl.setText(data.get('title', 'Unknown'))
        self.year_lbl.setText(str(data.get('year', '')))
        self.overview_lbl.setText(data.get('overview', 'No description available.'))

    def update_episode(self, ep_data_list):
        if not ep_data_list:
            self.ep_frame.hide()
            return
        
        if not isinstance(ep_data_list, list):
            ep_data_list = [ep_data_list]
            
        ids = []
        titles = []
        for ep in ep_data_list:
            s = ep.get('season_number', '?')
            e = ep.get('episode_number', '?')
            ids.append(f"S{str(s).zfill(2)}E{str(e).zfill(2)}")
            titles.append(ep.get('name', 'Untitled Episode'))
            
        self.ep_id_lbl.setText(", ".join(ids))
        self.ep_title_lbl.setText(" / ".join(titles))
        self.ep_frame.show()

    def update_status(self, status):
        if not status:
            self.status_badge.hide()
            return
        color = Theme.STATUS_COLORS.get(status, '#64748B')
        self.status_badge.setText(status)
        self.status_badge.setStyleSheet(f"""
            QLabel {{
                color: {color}; background-color: {color}20;
                border: 1px solid {color}50; border-radius: 12px;
                font-weight: 800; font-size: 10px; padding: 2px 8px;
            }}
        """)
        self.status_badge.show()

    def clear(self):
        self.title_lbl.setText("Select a file")
        self.year_lbl.setText("")
        self.overview_lbl.setText("Select a file to see details.")
        self.status_badge.hide()
        self.ep_frame.hide()
