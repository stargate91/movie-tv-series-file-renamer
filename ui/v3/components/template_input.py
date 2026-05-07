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
        ("{ParentName}", "Parent movie/show name"),
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

# Flat tag lists for extras contexts (no submenus needed)
EXTRAS_TAGS = [
    ("{ParentName}", "Parent movie/show name"),
    ("{ExtraCategory}", "Type of extra (e.g., Trailer)"),
    ("{Original}", "Original filename"),
]

EXTRAS_LANG_TAGS = [
    ("{ParentName}", "Parent movie/show name"),
    ("{ExtraCategory}", "Type of extra (e.g., Trailer)"),
    ("{Original}", "Original filename"),
    ("{Language}", "Extracted language code"),
]

# Movie file/folder context: curated metadata + Technical submenu
MOVIE_TAGS = [
    ("{TMDB_ID}", "TMDB database ID"),
    ("{IMDB_ID}", "IMDB database ID"),
    ("{Title}", "Movie title"),
    ("{Year}", "Release year"),
    ("{RatingImdb}", "IMDB rating"),
    ("{OriginalTitle}", "Original language title"),
    ("{ReleaseDate}", "Full release date"),
    ("{Part}", "Formatted part number (e.g., Part 1)"),
    ("{PartRaw}", "Raw part number"),
    ("{Custom}", "Custom user variable"),
    ("{Edition}", "Release edition (e.g., Extended)"),
]

COLLECTION_TAGS = [
    ("{Collection}", "Box Set or Collection name"),
]

# TV/Episode file/folder context: curated series+episode tags + Technical submenu
TV_TAGS = [
    ("{TMDB_ID}", "Series TMDB ID"),
    ("{IMDB_ID}", "Series IMDB ID"),
    ("{ShowTitle}", "Series title"),
    ("{SeriesOriginalTitle}", "Series original title"),
    ("{Network}", "TV Network or Streaming service"),
    ("{EpisodeTMDB_ID}", "Episode TMDB ID"),
    ("{EpisodeIMDB_ID}", "Episode IMDB ID"),
    ("{Season}", "Formatted season (e.g., S01)"),
    ("{Episode}", "Formatted episode (e.g., E01)"),
    ("{EpisodeTitle}", "Title of the episode"),
    ("{EpisodeAirDate}", "Episode air date"),
    ("{EpisodeAirYear}", "Episode air year"),
    ("{EpisodeRatingImdb}", "Episode IMDB rating"),
    ("{Part}", "Formatted part number (e.g., Part 1)"),
    ("{PartRaw}", "Raw part number"),
    ("{Custom}", "Custom user variable"),
]

# Season folder context
SEASON_FOLDER_TAGS = [
    ("{SeasonTMDB_ID}", "Season TMDB ID"),
    ("{Season}", "Formatted season (e.g., S01)"),
    ("{SeasonName}", "Name of the season"),
    ("{SeasonAirDate}", "Season air date"),
    ("{SeasonEpisodeCount}", "Episode count for the season"),
    ("{SeasonResolution}", "Mixed resolution for the season"),
    ("{Custom}", "Custom user variable"),
]

# Series (show) folder context
SERIES_FOLDER_TAGS = [
    ("{TMDB_ID}", "Series TMDB ID"),
    ("{IMDB_ID}", "Series IMDB ID"),
    ("{ShowTitle}", "Series title"),
    ("{Director}", "Director name"),
    ("{SeriesRating}", "Series IMDB rating"),
    ("{SeriesOriginalTitle}", "Series original title"),
    ("{FirstAirDate}", "First air date"),
    ("{LastAirDate}", "Last air date"),
    ("{FirstAirYear}", "First air year"),
    ("{LastAirYear}", "Last air year"),
    ("{YearRange}", "Year range (e.g., 2010-2015)"),
    ("{EpisodeCount}", "Total number of episodes"),
    ("{SeasonCount}", "Total number of seasons"),
    ("{SeriesStatus}", "Series status (e.g., Ended)"),
    ("{SeriesType}", "Series type (e.g., Scripted)"),
    ("{Network}", "TV Network or Streaming service"),
    ("{SeriesResolution}", "Mixed resolution across series"),
]

def get_menu_items(context):
    # Simple flat contexts
    if context == "extras":
        return EXTRAS_TAGS
    if context == "extras_lang":
        return EXTRAS_LANG_TAGS
    if context == "collection":
        return COLLECTION_TAGS
    if context == "season":
        return SEASON_FOLDER_TAGS
    if context == "series":
        return SERIES_FOLDER_TAGS
    if context == "movie":
        return {"_flat": MOVIE_TAGS, "Technical": GROUPS["Technical"]}
    if context == "tv":
        return {"_flat": TV_TAGS, "Technical": GROUPS["Technical"]}

    # Fallback for "all" or unknown contexts
    allowed = ["Media Info", "TV Specific", "Technical", "Extras & System"]
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
        if isinstance(items, list):
            # Flat list — no submenus
            for var, desc in items:
                action = self.menu.addAction(f"{var}  —  {desc}")
                action.setData(var)
        else:
            for group, tags in items.items():
                if group == "_flat":
                    # Top-level flat tags (no submenu)
                    for var, desc in tags:
                        action = self.menu.addAction(f"{var}  —  {desc}")
                        action.setData(var)
                else:
                    sub = self.menu.addMenu(group)
                    for var, desc in tags:
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
