import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem, QHeaderView, QLabel)
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from core.i18n import T

class DataSheetDialog(QDialog):
    """Full data popup with tabs for all associated metadata."""

    def __init__(self, file_data, media_data, ep_data_list, season_data, children, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("discovery.inspector.data_sheet.title"))
        self.setMinimumSize(750, 600)
        self.setStyleSheet(Theme.get_data_sheet_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        tabs = QTabWidget()
        tabs.setDocumentMode(True) # Premium look

        is_extra = file_data and file_data.get('category') in ('extra', 'subtitle', 'audio', 'metadata', 'image')

        # 1. Media Section (Multi-language aware)
        if media_data and not is_extra:
            details = {}
            if media_data.get('details_json'):
                try:
                    parsed = json.loads(media_data['details_json'])
                    if isinstance(parsed, dict) and 'tmdb_id' not in parsed: # It's a lang-mapped dict
                        details = parsed
                except: pass

            if details:
                media_lang_tabs = QTabWidget()
                for lang, lang_data in details.items():
                    lang_label = lang # Could be mapped to friendly name
                    media_lang_tabs.addTab(self._build_tree_tab(self._media_to_tree(media_data, lang_data)), lang_label)
                tabs.addTab(media_lang_tabs, T("discovery.inspector.data_sheet.tabs.media"))
            else:
                tabs.addTab(self._build_tree_tab(self._media_to_tree(media_data)), T("discovery.inspector.data_sheet.tabs.media"))

        # 2. Episode Section (Multi-language aware)
        if (ep_data_list or season_data) and not is_extra:
            # For simplicity, we check the first episode's languages if ep_list exists
            ep_details = {}
            if ep_data_list and ep_data_list[0].get('details_json'):
                try:
                    parsed = json.loads(ep_data_list[0]['details_json'])
                    if isinstance(parsed, dict) and 'tmdb_id' not in parsed:
                        ep_details = parsed
                except: pass
            
            count = len(ep_data_list or [])
            label = T("discovery.inspector.data_sheet.tabs.episodes") if count > 1 else T("discovery.inspector.data_sheet.tabs.episode")
            
            if ep_details:
                ep_lang_tabs = QTabWidget()
                # We need to collect ALL languages available across episodes if possible, 
                # but usually they are fetched together.
                for lang in ep_details.keys():
                    # Build tree for this language
                    lang_ep_list = []
                    for ep in ep_data_list:
                        ep_parsed = {}
                        try:
                            ep_details_raw = ep.get('details_json')
                            if ep_details_raw:
                                p = json.loads(ep_details_raw)
                                if isinstance(p, dict) and lang in p:
                                    ep_parsed = p[lang]
                        except: pass
                        lang_ep_list.append((ep, ep_parsed))
                    
                    ep_lang_tabs.addTab(self._build_tree_tab(self._episode_to_tree(lang_ep_list, season_data)), lang)
                tabs.addTab(ep_lang_tabs, label)
            else:
                # Wrap existing ep_list into (ep, None) tuple list for helper
                simple_list = [(ep, None) for ep in ep_data_list] if ep_data_list else []
                tabs.addTab(self._build_tree_tab(self._episode_to_tree(simple_list, season_data)), label)

        # 3. Technical & Other
        tabs.addTab(self._build_tree_tab(self._tech_to_tree(file_data)), T("discovery.inspector.data_sheet.tabs.technical"))
        
        if children:
            tabs.addTab(self._build_children_tab(children), T("discovery.inspector.data_sheet.tabs.linked", count=len(children)))

        if media_data and media_data.get('details_json') and not is_extra:
            tabs.addTab(self._build_raw_tab(media_data['details_json']), T("discovery.inspector.data_sheet.tabs.raw"))

        layout.addWidget(tabs)

        close_btn = QPushButton(T("common.close"))
        close_btn.setFixedWidth(120)
        close_btn.setStyleSheet(Theme.get_primary_button_style())
        close_btn.clicked.connect(self.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _build_tree_tab(self, items):
        tree = QTreeWidget()
        tree.setHeaderLabels([T("discovery.inspector.data_sheet.cols.property"), T("discovery.inspector.data_sheet.cols.value")])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setStyleSheet(Theme.get_tree_style())
        header = tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for key, value in items:
            tree.addTopLevelItem(QTreeWidgetItem([str(key), str(value)]))
        return tree

    def _build_children_tab(self, children):
        tree = QTreeWidget()
        tree.setHeaderLabels([T("discovery.inspector.data_sheet.cols.name"), T("discovery.inspector.data_sheet.cols.category"), T("discovery.inspector.data_sheet.cols.status")])
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

    def _media_to_tree(self, m, lang_data=None):
        items = []
        
        # Merge language data if provided
        data = m.copy()
        if lang_data:
            data.update(lang_data)
            # TMDB name vs title consistency
            if 'name' in lang_data and 'title' not in lang_data:
                data['title'] = lang_data['name']

        for key, label in [
            ('title', T('discovery.inspector.fields.title')), 
            ('original_title', T('discovery.inspector.fields.original_title')), 
            ('year', T('discovery.inspector.fields.year')),
            ('media_type', T('discovery.inspector.fields.type')), 
            ('genres', T('discovery.inspector.fields.genres')), 
            ('tagline', T('discovery.inspector.fields.tagline')),
            ('overview', T('discovery.inspector.fields.overview')), 
            ('director', T('discovery.inspector.fields.director')), 
            ('cast', T('discovery.inspector.fields.cast')),
            ('runtime', T('discovery.inspector.fields.runtime')), 
            ('release_date', T('discovery.inspector.fields.release_date')),
            ('rating_tmdb', T('discovery.inspector.fields.rating')), 
            ('rating_imdb', 'IMDb Rating'),
            ('rating_rotten', 'Rotten Tomatoes'),
            ('rating_metacritic', 'Metacritic'),
            ('origin_country', 'Origin Country'),
            ('original_language', 'Original Language'),
            ('languages', 'Languages'),
            ('budget', 'Budget'),
            ('revenue', 'Revenue'),
            ('popularity', 'Popularity'),
            ('vote_count_tmdb', 'Vote Count (TMDB)'),
            ('collection', 'Collection'),
            ('tmdb_id', T('discovery.inspector.fields.tmdb_id')), 
            ('imdb_id', T('discovery.inspector.fields.imdb_id')),
        ]:
            val = data.get(key)
            if val is not None and val != "":
                items.append((label, str(val)))
        return items

    def _episode_to_tree(self, ep_list, season):
        """ep_list is now a list of (ep_flat, ep_lang_data) tuples."""
        items = []
        if season:
            for key, label in [
                ('name', T('discovery.inspector.fields.season_name')), 
                ('season_number', T('discovery.inspector.fields.season_num')), 
                ('air_date', T('discovery.inspector.fields.season_air_date')),
                ('episode_count', 'Episode Count'),
                ('poster_path', 'Season Poster Path'),
                ('overview', T('discovery.inspector.fields.overview'))
            ]:
                val = season.get(key)
                if val is not None and val != "":
                    items.append((label, str(val)))
        
        if ep_list:
            for ep_flat, ep_lang in ep_list:
                # Merge lang data
                data = ep_flat.copy()
                if ep_lang:
                    data.update(ep_lang)
                
                items.append(('', T('discovery.inspector.fields.episode_divider', count=data.get("episode_number"))))
                for key, label in [
                    ('name', T('discovery.inspector.fields.episode_title')), 
                    ('season_number', T('edit_file.fields.season')), 
                    ('episode_number', T('edit_file.fields.episode')), 
                    ('air_date', T('discovery.inspector.fields.air_date')), 
                    ('runtime', T('discovery.inspector.fields.runtime')),
                    ('vote_average', 'Episode Rating (TMDB)'),
                    ('vote_count_tmdb', 'Vote Count (TMDB)'),
                    ('imdb_id', T('discovery.inspector.fields.imdb_id')),
                    ('tmdb_id', T('discovery.inspector.fields.tmdb_id')),
                    ('still_path', 'Episode Still Path'),
                    ('overview', T('discovery.inspector.fields.overview'))
                ]:
                    val = data.get(key)
                    if val is not None and val != "":
                        items.append((label, str(val)))
        return items

    def _tech_to_tree(self, f):
        items = []
        if f:
            items.append((T('discovery.inspector.data_sheet.cols.name'), f.get('file_name', '-')))
            items.append((T('discovery.inspector.fields.path'), f.get('current_path', '-')))
            size_bytes = f.get('size_bytes', 0)
            if size_bytes:
                gb = size_bytes / (1024**3)
                items.append((T('discovery.inspector.fields.size'), f"{gb:.2f} GB" if gb >= 1 else f"{size_bytes/(1024**2):.1f} MB"))
                
            cat = f.get('category')
            if cat in ('extra', 'subtitle', 'audio', 'metadata', 'image'):
                items.append(('Category', cat.capitalize()))
                
                sub_cat = f.get('sub_category')
                if sub_cat:
                    items.append(('Extra Type', sub_cat))
                
                if cat in ('subtitle', 'audio'):
                    lang = f.get('language')
                    if lang:
                        items.append(('Language', lang))
                        
                part = f.get('part_number')
                if part:
                    items.append(('Part Number', str(part)))
                    
                parent_id = f.get('parent_file_id')
                if parent_id:
                    try:
                        import sqlite3, os
                        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
                        db_path = os.path.join(base_dir, 'data', 'db', 'library.db')
                        with sqlite3.connect(db_path) as conn:
                            row = conn.execute("SELECT current_path FROM media_files WHERE id = ?", (parent_id,)).fetchone()
                            if row:
                                items.append(('Parent Path', row[0]))
                            else:
                                items.append(('Parent ID', str(parent_id)))
                    except Exception as e:
                        items.append(('Parent ID', str(parent_id)))
            else:
                for key, label in [
                    ('duration', 'Duration (seconds)'),
                    ('resolution', T('discovery.inspector.fields.resolution')), 
                    ('video_codec', T('discovery.inspector.fields.codec')), 
                    ('video_bitrate', 'Video Bitrate (bps)'),
                    ('framerate', 'Framerate (fps)'),
                    ('bit_depth', 'Bit Depth'),
                    ('hdr_type', 'HDR Format'),
                    ('audio_codec', T('discovery.inspector.fields.audio')), 
                    ('audio_channels', 'Audio Channels'),
                    ('audio_bitrate', 'Audio Bitrate (bps)'),
                    ('edition', T('discovery.inspector.fields.edition'))
                ]:
                    val = f.get(key)
                    if val is not None and val != "":
                        items.append((label, str(val)))
        return items
