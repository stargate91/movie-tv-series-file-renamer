from PySide6.QtWidgets import QLineEdit, QToolButton, QMenu
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme

GROUPS = {
    "Media Info": [
        ("{Title}", "Movie or TV Show title"),
        ("{OriginalTitle}", "Original language title"),
        ("{Year}", "Release year"),
        ("{ReleaseDate}", "Full release date"),
        ("{Collection}", "Box Set or Collection name"),
        ("{Director}", "Director name"),
        ("{Cast}", "Cast members"),
        ("{Genres}", "Media genres"),
        ("{Runtime}", "Duration in minutes"),
        ("{Edition}", "Release edition (e.g., Extended)"),
    ],
    "TV Specific": [
        ("{ShowTitle}", "Name of the TV show"),
        ("{Season}", "Formatted season (e.g., S01)"),
        ("{Episode}", "Formatted episode (e.g., E01)"),
        ("{EpisodeTitle}", "Title of the episode"),
        ("{SeasonName}", "Name of the season"),
        ("{YearRange}", "Series run (e.g., 2010-2015)"),
        ("{Network}", "TV Network or Streaming service"),
    ],
    "Technical": [
        ("{Resolution}", "Video resolution (e.g., 1080p, 4K)"),
        ("{VideoCodec}", "Video codec (e.g., x264, HEVC)"),
        ("{AudioCodec}", "Audio codec (e.g., AC3, DTS)"),
        ("{AudioChannels}", "Audio channels (e.g., 5.1)"),
        ("{HDR}", "HDR format (e.g., HDR10)"),
        ("{BitDepth}", "Color depth (e.g., 10bit)"),
        ("{Framerate}", "Video framerate"),
        ("{VideoBitrate}", "Video bitrate"),
    ],
    "Extras & System": [
        ("{Original}", "Original filename"),
        ("{Language}", "Extracted language code"),
        ("{ExtraCategory}", "Type of extra (e.g., Trailer)"),
        ("{Part}", "Formatted part number (e.g., Part 1)"),
        ("{PartRaw}", "Raw part number"),
        ("{Custom}", "Custom user variable"),
        ("{TMDB_ID}", "TMDB database ID"),
        ("{IMDB_ID}", "IMDB database ID"),
    ]
}

def get_menu_items(context):
    allowed = ["Technical", "Extras & System"]
    if context in ("movie", "all"): allowed.insert(0, "Media Info")
    if context in ("tv", "all"): allowed.insert(1, "TV Specific")
    
    res = {}
    for k in allowed:
        if k in GROUPS: res[k] = GROUPS[k]
    return res

class TemplateLineEdit(QLineEdit):
    def __init__(self, context="all", parent=None):
        super().__init__(parent)
        self.context = context
        
        # Override padding to make room for the button
        base_style = Theme.get_settings_input_style()
        self.setStyleSheet(base_style + " QLineEdit { padding-right: 40px; }")
        
        self.btn = QToolButton(self)
        self.btn.setText("{}")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                color: {Theme.TEXT_MUTED};
                font-weight: 800;
                font-size: 15px;
                font-family: 'Courier New', monospace;
            }}
            QToolButton:hover {{ color: {Theme.PRIMARY}; }}
            QToolButton::menu-indicator {{ image: none; }}
        """)
        self.btn.setPopupMode(QToolButton.InstantPopup)
        
        self.menu = QMenu(self)
        # QMenu styling is globally handled by common.py
        self.btn.setMenu(self.menu)
        
        self._populate_menu()
        
    def _populate_menu(self):
        items = get_menu_items(self.context)
        for group, vars in items.items():
            sub = self.menu.addMenu(group)
            for var, desc in vars:
                action = sub.addAction(f"{var}  —  {desc}")
                action.setData(var)
        self.menu.triggered.connect(self._on_action)

    def _on_action(self, action):
        var = action.data()
        if var:
            self.insert(var)
            self.setFocus()
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        btn_w = 35
        self.btn.setGeometry(self.width() - btn_w - 2, 0, btn_w, self.height())
