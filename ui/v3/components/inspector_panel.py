import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
                             QPushButton, QScrollArea, QStackedWidget, QDialog, QTabWidget,
                             QTextEdit, QTreeWidget, QTreeWidgetItem, QHeaderView, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QPixmap, QFont, QColor, QPainter, QPainterPath
from ui.v3.styles.theme import Theme


class PosterCarousel(QWidget):
    """A stacked poster widget that shows up to 3 layers for TV:
       Series poster (back) → Season poster (middle) → Episode still (front).
       For movies, just one poster is shown."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(300, 440)
        self._posters = []   # list of QPixmap (up to 3)
        self._labels = []    # list of str labels
        self._current = 0    # which one is "active" / on top

    def set_single_poster(self, pixmap):
        """Movie mode: one poster, no carousel."""
        self._posters = [pixmap] if pixmap else []
        self._labels = ["Poster"]
        self._current = 0
        self.update()

    def set_tv_posters(self, series_pix=None, season_pix=None, episode_pix=None):
        """TV mode: up to 3 layered posters."""
        self._posters = []
        self._labels = []
        for pix, label in [(series_pix, "Series"), (season_pix, "Season"), (episode_pix, "Episode")]:
            if pix and not pix.isNull():
                self._posters.append(pix)
                self._labels.append(label)
        self._current = len(self._posters) - 1 if self._posters else 0
        self.update()

    def clear(self):
        self._posters = []
        self._labels = []
        self._current = 0
        self.update()

    def mousePressEvent(self, event):
        """Cycle through posters on click."""
        if len(self._posters) > 1:
            self._current = (self._current + 1) % len(self._posters)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()

        if not self._posters:
            # Empty state
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, 12, 12)
            painter.setClipPath(path)
            painter.fillRect(0, 0, w, h, QColor(Theme.SURFACE))
            painter.setPen(QColor(Theme.TEXT_DIM))
            painter.setFont(QFont("Inter", 12, QFont.DemiBold))
            painter.drawText(0, 0, w, h, Qt.AlignCenter, "No Poster")
            return

        if len(self._posters) == 1:
            # Single poster mode (movies)
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, 12, 12)
            painter.setClipPath(path)
            scaled = self._posters[0].scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            return

        # Multi-poster stack mode (TV shows)
        total = len(self._posters)
        offset = 8  # pixel offset per card layer

        for i in range(total):
            # Draw from back to front, with active on top
            idx = (self._current - (total - 1 - i)) % total

            layer_offset = (total - 1 - i) * offset
            card_w = w - layer_offset * 2
            card_h = h - layer_offset * 2
            card_x = layer_offset
            card_y = layer_offset

            # Scale opacity for back cards
            opacity = 0.35 + 0.65 * (i / (total - 1)) if total > 1 else 1.0
            painter.setOpacity(opacity)

            path = QPainterPath()
            path.addRoundedRect(card_x, card_y, card_w, card_h, 12, 12)
            painter.setClipPath(path)

            # Shadow for depth
            if i < total - 1:
                painter.fillRect(card_x, card_y, card_w, card_h, QColor(0, 0, 0, 80))

            scaled = self._posters[idx].scaled(card_w, card_h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            px = card_x + (card_w - scaled.width()) // 2
            py = card_y + (card_h - scaled.height()) // 2
            painter.drawPixmap(px, py, scaled)

            painter.setClipping(False)

        # Draw label badge on the front card
        painter.setOpacity(1.0)
        label_text = self._labels[self._current] if self._current < len(self._labels) else ""
        if label_text and total > 1:
            font = QFont("Inter", 9, QFont.Bold)
            painter.setFont(font)
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(label_text) + 16
            text_h = 22

            badge_x = w - text_w - 8
            badge_y = 8

            badge_path = QPainterPath()
            badge_path.addRoundedRect(badge_x, badge_y, text_w, text_h, 6, 6)
            painter.fillPath(badge_path, QColor(0, 0, 0, 160))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_x, badge_y, text_w, text_h, Qt.AlignCenter, label_text)

            # Dot indicators
            dot_y = h - 16
            dot_total_w = total * 12
            dot_start_x = (w - dot_total_w) // 2
            for di in range(total):
                cx = dot_start_x + di * 12 + 4
                if di == self._current:
                    painter.setBrush(QColor(Theme.PRIMARY))
                else:
                    painter.setBrush(QColor(255, 255, 255, 100))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(cx, dot_y, 6, 6)


class DataSheetDialog(QDialog):
    """Full data popup with tabs for all associated metadata."""

    def __init__(self, file_data, media_data, episode_data, season_data, children, tech_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📋 Data Sheet")
        self.setMinimumSize(700, 550)
        self.setStyleSheet(f"""
            QDialog {{ background: {Theme.BACKGROUND}; }}
            QTabWidget::pane {{ border: 1px solid {Theme.BORDER}; border-radius: 8px; background: {Theme.SURFACE_DARK}; }}
            QTabBar::tab {{ background: {Theme.SURFACE}; color: {Theme.TEXT_MUTED}; padding: 8px 18px; border: 1px solid {Theme.BORDER}; border-bottom: none; border-radius: 6px 6px 0 0; font-weight: 600; }}
            QTabBar::tab:selected {{ background: {Theme.SURFACE_DARK}; color: {Theme.TEXT_MAIN}; border-bottom: 2px solid {Theme.PRIMARY}; }}
            QTextEdit {{ background: {Theme.SURFACE}; color: {Theme.TEXT_MAIN}; border: 1px solid {Theme.BORDER}; border-radius: 6px; font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px; padding: 8px; }}
            QTreeWidget {{ background: {Theme.SURFACE}; color: {Theme.TEXT_MAIN}; border: 1px solid {Theme.BORDER}; border-radius: 6px; }}
            QTreeWidget::item {{ padding: 4px 0; }}
            QHeaderView::section {{ background: {Theme.SURFACE_LIGHT}; color: {Theme.TEXT_MUTED}; font-weight: 700; border: none; padding: 6px; }}
            QLabel {{ color: {Theme.TEXT_MAIN}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        tabs = QTabWidget()

        # --- Tab 1: Media Info ---
        if media_data:
            media_tab = self._build_tree_tab(self._media_to_tree(media_data))
            tabs.addTab(media_tab, "🎬 Media Info")

        # --- Tab 2: Episode/Season ---
        if episode_data or season_data:
            ep_tab = self._build_tree_tab(self._episode_to_tree(episode_data, season_data))
            tabs.addTab(ep_tab, "📺 Episode")

        # --- Tab 3: Technical ---
        tech_tab = self._build_tree_tab(self._tech_to_tree(file_data, tech_info))
        tabs.addTab(tech_tab, "⚙️ Technical")

        # --- Tab 4: Children Files ---
        if children:
            children_tab = self._build_children_tab(children)
            tabs.addTab(children_tab, f"📎 Linked Files ({len(children)})")

        # --- Tab 5: Raw API JSON ---
        if media_data and media_data.get('details_json'):
            raw_tab = QTextEdit()
            raw_tab.setReadOnly(True)
            try:
                parsed = json.loads(media_data['details_json'])
                raw_tab.setPlainText(json.dumps(parsed, indent=2, ensure_ascii=False))
            except:
                raw_tab.setPlainText(str(media_data['details_json']))
            tabs.addTab(raw_tab, "{ } Raw API")

        if episode_data and episode_data.get('details_json'):
            ep_raw_tab = QTextEdit()
            ep_raw_tab.setReadOnly(True)
            try:
                parsed = json.loads(episode_data['details_json'])
                ep_raw_tab.setPlainText(json.dumps(parsed, indent=2, ensure_ascii=False))
            except:
                ep_raw_tab.setPlainText(str(episode_data['details_json']))
            tabs.addTab(ep_raw_tab, "{ } Raw Episode")

        layout.addWidget(tabs)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(120)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: {Theme.PRIMARY}; color: white; border-radius: 6px; padding: 8px 16px; font-weight: 700; border: none; }}
            QPushButton:hover {{ background: {Theme.PRIMARY_HOVER}; }}
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _build_tree_tab(self, items):
        tree = QTreeWidget()
        tree.setHeaderLabels(["Property", "Value"])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setStyleSheet(tree.styleSheet() + f"QTreeWidget {{ alternate-background-color: {Theme.SURFACE_DARK}; }}")

        header = tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        for key, value in items:
            item = QTreeWidgetItem([str(key), str(value)])
            item.setToolTip(1, str(value))
            tree.addTopLevelItem(item)

        return tree

    def _build_children_tab(self, children):
        tree = QTreeWidget()
        tree.setHeaderLabels(["File Name", "Category", "Status"])
        tree.setRootIsDecorated(False)

        header = tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        for child in children:
            item = QTreeWidgetItem([
                child.get('file_name', '?'),
                child.get('category', '?'),
                child.get('match_status', '?').upper()
            ])
            tree.addTopLevelItem(item)
        return tree

    def _media_to_tree(self, m):
        items = []
        for key, label in [
            ('title', 'Title'), ('original_title', 'Original Title'), ('year', 'Year'),
            ('media_type', 'Type'), ('genres', 'Genres'), ('tagline', 'Tagline'),
            ('overview', 'Overview'), ('director', 'Director'), ('cast', 'Cast'),
            ('runtime', 'Runtime (min)'), ('release_date', 'Release Date'),
            ('rating_tmdb', 'TMDB Rating'), ('vote_count_tmdb', 'TMDB Votes'),
            ('rating_imdb', 'IMDb Rating'), ('votes_imdb', 'IMDb Votes'),
            ('budget', 'Budget'), ('revenue', 'Revenue'), ('popularity', 'Popularity'),
            ('original_language', 'Original Language'), ('origin_country', 'Country'),
            ('status', 'Status'), ('tmdb_id', 'TMDB ID'), ('imdb_id', 'IMDb ID'),
            ('number_of_seasons', 'Seasons'), ('number_of_episodes', 'Episodes'),
            ('first_air_date', 'First Aired'), ('last_air_date', 'Last Aired'),
        ]:
            val = m.get(key)
            if val is not None and val != '' and val != 0:
                items.append((label, str(val)))
        return items

    def _episode_to_tree(self, ep, season):
        items = []
        if season:
            for key, label in [('name', 'Season Name'), ('season_number', 'Season #'),
                                ('air_date', 'Season Air Date'), ('episode_count', 'Episodes in Season')]:
                val = season.get(key)
                if val is not None and val != '':
                    items.append((label, str(val)))
            if season.get('overview'):
                items.append(('Season Overview', season['overview']))
        if ep:
            items.append(('', '──── Episode ────'))
            for key, label in [('name', 'Episode Title'), ('season_number', 'Season'),
                                ('episode_number', 'Episode'), ('air_date', 'Air Date'),
                                ('runtime', 'Runtime (min)'), ('overview', 'Episode Overview'),
                                ('vote_average', 'TMDB Rating'), ('vote_count_tmdb', 'Votes'),
                                ('tmdb_id', 'TMDB Ep ID'), ('imdb_id', 'IMDb Ep ID')]:
                val = ep.get(key)
                if val is not None and val != '':
                    items.append((label, str(val)))
        return items

    def _tech_to_tree(self, f, tech):
        items = []
        if f:
            import os
            items.append(('File Name', f.get('file_name', '-')))
            items.append(('Full Path', f.get('current_path', '-')))
            items.append(('Original Path', f.get('original_path', '-')))
            items.append(('Category', f.get('category', '-')))

            size_bytes = f.get('size_bytes', 0)
            if size_bytes:
                gb = size_bytes / (1024**3)
                items.append(('File Size', f"{gb:.2f} GB" if gb >= 1 else f"{size_bytes/(1024**2):.1f} MB"))

            for key, label in [
                ('resolution', 'Resolution'), ('video_codec', 'Video Codec'),
                ('audio_codec', 'Audio Codec'), ('audio_channels', 'Audio Channels'),
                ('fn_title', 'Parsed Title'), ('fn_year', 'Parsed Year'),
                ('fn_media_type', 'Parsed Type'), ('fd_title', 'Folder Title'),
                ('fd_year', 'Folder Year'), ('nfo_imdb_id', 'NFO IMDb ID'),
                ('nfo_title', 'NFO Title'), ('internal_title', 'MKV Internal Title'),
                ('edition', 'Edition'),
            ]:
                val = f.get(key)
                if val is not None and val != '':
                    items.append((label, str(val)))
        return items


class InspectorPanel(QFrame):
    """Right-side panel for showing metadata details and resolving conflicts."""

    match_selected = Signal(int, dict) # file_id, media_item_data

    def __init__(self):
        super().__init__()
        self.setFixedWidth(340)
        self.setObjectName("Inspector")
        self.setStyleSheet(f"""
            QFrame#Inspector {{
                background-color: {Theme.SURFACE_DARK};
                border-left: 1px solid {Theme.BORDER};
            }}
            QLabel {{ color: {Theme.TEXT_MAIN}; }}
        """)
        self._current_file_data = None
        self._current_media_data = None
        self._current_episode_data = None
        self._current_season_data = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Poster Carousel
        self.poster_carousel = PosterCarousel()
        layout.addWidget(self.poster_carousel, alignment=Qt.AlignHCenter)

        # Title
        self.title_label = QLabel("Select a file")
        self.title_label.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {Theme.TEXT_MAIN}; line-height: 1.3;")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # Subtitle row: Year + Status
        subtitle_layout = QHBoxLayout()
        subtitle_layout.setSpacing(10)

        self.year_label = QLabel("")
        self.year_label.setStyleSheet(f"font-size: 15px; color: {Theme.PRIMARY}; font-weight: 700;")

        self.status_badge = QLabel("")
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setFixedHeight(24)
        self.status_badge.hide()

        subtitle_layout.addWidget(self.year_label)
        subtitle_layout.addStretch()
        subtitle_layout.addWidget(self.status_badge)
        layout.addLayout(subtitle_layout)

        # Episode info (hidden for movies)
        self.episode_frame = QFrame()
        self.episode_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.SURFACE};
                border-radius: 10px;
                border: 1px solid {Theme.BORDER};
            }}
        """)
        ep_layout = QVBoxLayout(self.episode_frame)
        ep_layout.setContentsMargins(14, 12, 14, 12)
        ep_layout.setSpacing(4)

        self.episode_label = QLabel("")
        self.episode_label.setStyleSheet(f"font-size: 13px; color: {Theme.PRIMARY}; font-weight: 700; border: none;")

        self.episode_title_label = QLabel("")
        self.episode_title_label.setWordWrap(True)
        self.episode_title_label.setStyleSheet(f"font-size: 14px; color: {Theme.TEXT_MAIN}; font-weight: 600; border: none;")

        ep_layout.addWidget(self.episode_label)
        ep_layout.addWidget(self.episode_title_label)
        self.episode_frame.hide()
        layout.addWidget(self.episode_frame)

        # Overview / Plot (Scrollable)
        self.plot_label = QLabel("")
        self.plot_label.setWordWrap(True)
        self.plot_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; line-height: 1.5; font-size: 12px;")
        self.plot_label.setAlignment(Qt.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(self.plot_label)
        layout.addWidget(scroll, 1)  # stretch factor so it fills available space

        # Technical Info Section (compact)
        self.tech_header = QLabel("TECHNICAL")
        self.tech_header.setStyleSheet(f"font-weight: 800; font-size: 10px; color: {Theme.TEXT_DIM}; letter-spacing: 1.5px;")
        layout.addWidget(self.tech_header)

        self.tech_frame = QFrame()
        self.tech_frame.setStyleSheet(f"background-color: {Theme.SURFACE}; border-radius: 10px; border: 1px solid {Theme.BORDER};")
        self.tech_layout = QGridLayout(self.tech_frame)
        self.tech_layout.setContentsMargins(12, 10, 12, 10)
        self.tech_layout.setSpacing(6)
        self.tech_layout.setColumnStretch(1, 1)

        # Pre-create labels for the grid
        self.labels = {}
        fields = [("RES", "RES"), ("CODEC", "CODEC"), ("AUDIO", "AUDIO"), ("SIZE", "SIZE")]
        for i, (key, label) in enumerate(fields):
            l1 = QLabel(label)
            l1.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-size: 9px; font-weight: 800; letter-spacing: 1px; border: none;")
            l2 = QLabel("-")
            l2.setStyleSheet(f"color: {Theme.TEXT_MAIN}; font-size: 12px; font-weight: 600; border: none;")
            self.tech_layout.addWidget(l1, i, 0)
            self.tech_layout.addWidget(l2, i, 1)
            self.labels[key] = l2

        layout.addWidget(self.tech_frame)

        # Check Data button
        self.data_sheet_btn = QPushButton("📋 Check Data")
        self.data_sheet_btn.setCursor(Qt.PointingHandCursor)
        self.data_sheet_btn.setFixedHeight(36)
        self.data_sheet_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.SURFACE_LIGHT};
                color: {Theme.TEXT_MAIN};
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                border: 1px solid {Theme.BORDER};
            }}
            QPushButton:hover {{
                background: {Theme.SURFACE_LIGHTER};
                border-color: {Theme.PRIMARY};
            }}
        """)
        self.data_sheet_btn.clicked.connect(self._open_data_sheet)
        layout.addWidget(self.data_sheet_btn)

    def set_empty(self):
        self.title_label.setText("Select a file")
        self.year_label.setText("")
        self.plot_label.setText("Select a file to see details and manage identification.")
        self.poster_carousel.clear()
        self.status_badge.hide()
        self.episode_frame.hide()
        for lbl in self.labels.values():
            lbl.setText("-")
        self._current_file_data = None
        self._current_media_data = None
        self._current_episode_data = None
        self._current_season_data = None

    def update_status(self, status_text):
        """Updates the status badge."""
        if not status_text:
            self.status_badge.hide()
            return

        color = Theme.STATUS_COLORS.get(status_text, '#64748B')
        self.status_badge.setText(status_text)
        self.status_badge.setFixedWidth(max(70, len(status_text) * 9 + 20))
        self.status_badge.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: {color}20;
                border: 1px solid {color}50;
                border-radius: 12px;
                font-weight: 800;
                font-size: 10px;
                letter-spacing: 0.5px;
                padding: 2px 8px;
            }}
        """)
        self.status_badge.show()

    def update_from_data(self, media_data, candidates=None):
        """Updates the panel with media information."""
        self._current_media_data = media_data
        self.title_label.setText(media_data.get('title', 'Unknown'))
        self.year_label.setText(str(media_data.get('year', '')))
        self.plot_label.setText(media_data.get('overview', 'No description available.'))

    def update_episode_info(self, episode_data, season_data=None):
        """Shows season/episode info for TV shows."""
        self._current_episode_data = episode_data
        self._current_season_data = season_data

        if not episode_data:
            self.episode_frame.hide()
            return

        s_num = episode_data.get('season_number', '?')
        e_num = episode_data.get('episode_number', '?')
        self.episode_label.setText(f"S{str(s_num).zfill(2)}E{str(e_num).zfill(2)}")

        ep_title = episode_data.get('name', '')
        self.episode_title_label.setText(ep_title if ep_title else "Untitled Episode")
        self.episode_frame.show()

    def update_tech_info(self, file_data):
        """Updates the technical details from file metadata."""
        self._current_file_data = file_data
        if not file_data:
            return

        # Use database column 'resolution'
        self.labels['RES'].setText(str(file_data.get('resolution') or '-'))

        codec = file_data.get('video_codec') or '-'
        self.labels['CODEC'].setText(str(codec).upper())

        audio = file_data.get('audio_codec') or '-'
        channels = file_data.get('audio_channels') or ''
        audio_text = f"{str(audio).upper()} {channels}".strip()
        self.labels['AUDIO'].setText(audio_text)

        # Use database column 'size_bytes'
        size_bytes = file_data.get('size_bytes', 0)
        size_gb = size_bytes / (1024*1024*1024)
        if size_gb >= 1:
            self.labels['SIZE'].setText(f"{size_gb:.2f} GB")
        else:
            self.labels['SIZE'].setText(f"{size_bytes/(1024*1024):.1f} MB")

    def _open_data_sheet(self):
        """Opens the detailed data sheet popup."""
        children = getattr(self, '_current_children', [])

        dialog = DataSheetDialog(
            file_data=self._current_file_data,
            media_data=self._current_media_data,
            episode_data=self._current_episode_data,
            season_data=self._current_season_data,
            children=children,
            tech_info=None,
            parent=self.window()
        )
        dialog.exec()

    # Keep legacy poster_label interface for backward compat
    @property
    def poster_label(self):
        """Backward compatibility: returns an object with .clear() and .setPixmap()."""
        return self._PosterCompat(self.poster_carousel)

    class _PosterCompat:
        def __init__(self, carousel):
            self._carousel = carousel

        def clear(self):
            self._carousel.clear()

        def setPixmap(self, pixmap):
            self._carousel.set_single_poster(pixmap)

        def setText(self, text):
            self._carousel.clear()
