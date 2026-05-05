import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem, QHeaderView, QLabel)
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme

class DataSheetDialog(QDialog):
    """Full data popup with tabs for all associated metadata."""

    def __init__(self, file_data, media_data, ep_data_list, season_data, children, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📋 Data Sheet")
        self.setMinimumSize(750, 600)
        # ... (CSS stays same)
        self.setStyleSheet(f"""
            QDialog {{ background: {Theme.BACKGROUND}; }}
            QTabWidget::pane {{ border: 1px solid {Theme.BORDER}; border-radius: 8px; background: {Theme.SURFACE_DARK}; }}
            QTabBar::tab {{ background: {Theme.SURFACE}; color: {Theme.TEXT_MUTED}; padding: 10px 20px; border: 1px solid {Theme.BORDER}; border-bottom: none; border-radius: 6px 6px 0 0; font-weight: 600; }}
            QTabBar::tab:selected {{ background: {Theme.SURFACE_DARK}; color: {Theme.TEXT_MAIN}; border-bottom: 2px solid {Theme.PRIMARY}; }}
            QTextEdit {{ background: {Theme.SURFACE}; color: {Theme.TEXT_MAIN}; border: 1px solid {Theme.BORDER}; border-radius: 6px; font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px; padding: 8px; }}
            QTreeWidget {{ background: {Theme.SURFACE}; color: {Theme.TEXT_MAIN}; border: 1px solid {Theme.BORDER}; border-radius: 6px; }}
            QTreeWidget::item {{ padding: 6px 0; }}
            QHeaderView::section {{ background: {Theme.SURFACE_LIGHT}; color: {Theme.TEXT_MUTED}; font-weight: 700; border: none; padding: 8px; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        tabs = QTabWidget()

        if media_data:
            tabs.addTab(self._build_tree_tab(self._media_to_tree(media_data)), "🎬 Media Info")

        if ep_data_list or season_data:
            label = "📺 Episode(s)" if len(ep_data_list or []) > 1 else "📺 Episode"
            tabs.addTab(self._build_tree_tab(self._episode_to_tree(ep_data_list, season_data)), label)

        tabs.addTab(self._build_tree_tab(self._tech_to_tree(file_data)), "⚙️ Technical")
        # ... rest same
        if children:
            tabs.addTab(self._build_children_tab(children), f"📎 Linked Files ({len(children)})")

        if media_data and media_data.get('details_json'):
            tabs.addTab(self._build_raw_tab(media_data['details_json']), "{ } Raw API")

        layout.addWidget(tabs)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(120)
        close_btn.setStyleSheet(Theme.get_primary_button_style())
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
        tree.setStyleSheet(f"QTreeWidget {{ alternate-background-color: {Theme.SURFACE_DARK}; }}")
        header = tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for key, value in items:
            tree.addTopLevelItem(QTreeWidgetItem([str(key), str(value)]))
        return tree

    def _build_children_tab(self, children):
        tree = QTreeWidget()
        tree.setHeaderLabels(["File Name", "Category", "Status"])
        tree.setRootIsDecorated(False)
        for child in children:
            tree.addTopLevelItem(QTreeWidgetItem([
                child.get('file_name', '?'),
                child.get('category', '?'),
                child.get('match_status', '?').upper()
            ]))
        return tree

    def _build_raw_tab(self, data):
        raw = QTextEdit()
        raw.setReadOnly(True)
        try:
            parsed = json.loads(data) if isinstance(data, str) else data
            raw.setPlainText(json.dumps(parsed, indent=2, ensure_ascii=False))
        except:
            raw.setPlainText(str(data))
        return raw

    def _media_to_tree(self, m):
        items = []
        for key, label in [
            ('title', 'Title'), ('original_title', 'Original Title'), ('year', 'Year'),
            ('media_type', 'Type'), ('genres', 'Genres'), ('tagline', 'Tagline'),
            ('overview', 'Overview'), ('director', 'Director'), ('cast', 'Cast'),
            ('runtime', 'Runtime (min)'), ('release_date', 'Release Date'),
            ('rating_tmdb', 'TMDB Rating'), ('tmdb_id', 'TMDB ID'), ('imdb_id', 'IMDb ID'),
        ]:
            val = m.get(key)
            if val: items.append((label, str(val)))
        return items

    def _episode_to_tree(self, ep_list, season):
        items = []
        if season:
            for key, label in [('name', 'Season Name'), ('season_number', 'Season #'), ('air_date', 'Season Air Date')]:
                val = season.get(key)
                if val: items.append((label, str(val)))
        
        if ep_list:
            for ep in ep_list:
                items.append(('', f'──── Episode {ep.get("episode_number")} ────'))
                for key, label in [('name', 'Episode Title'), ('season_number', 'Season'), ('episode_number', 'Episode'), ('air_date', 'Air Date'), ('overview', 'Overview')]:
                    val = ep.get(key)
                    if val: items.append((label, str(val)))
        return items

    def _tech_to_tree(self, f):
        items = []
        if f:
            items.append(('File Name', f.get('file_name', '-')))
            items.append(('Path', f.get('current_path', '-')))
            size_bytes = f.get('size_bytes', 0)
            if size_bytes:
                gb = size_bytes / (1024**3)
                items.append(('Size', f"{gb:.2f} GB" if gb >= 1 else f"{size_bytes/(1024**2):.1f} MB"))
            for key, label in [('resolution', 'Resolution'), ('video_codec', 'Codec'), ('audio_codec', 'Audio'), ('edition', 'Edition')]:
                val = f.get(key)
                if val: items.append((label, str(val)))
        return items
