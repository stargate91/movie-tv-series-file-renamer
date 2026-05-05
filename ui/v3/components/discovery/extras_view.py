from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget
from ui.v3.styles.theme import Theme
from ui.v3.components.discovery_table import DiscoveryTable

class ExtrasView(QWidget):
    """
    Component for the 'Extras' tab with sub-categories and sub-type filtering.
    """
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._current_sub_filters = {
            "extra": "all", "image": "all", "subtitle": "all", "audio": "all", "metadata": "all"
        }
        self._raw_data = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {Theme.BORDER}; border-radius: 8px; background: {Theme.SURFACE_DARK}; }}
            QTabBar::tab {{ background: {Theme.SURFACE}; color: {Theme.TEXT_MUTED}; padding: 12px 24px; border: 1px solid {Theme.BORDER}; border-bottom: none; border-radius: 8px 8px 0 0; font-weight: 700; font-size: 13px; margin-right: 4px; }}
            QTabBar::tab:selected {{ background: {Theme.SURFACE_DARK}; color: {Theme.PRIMARY}; border-bottom: 2px solid {Theme.PRIMARY}; }}
            QTabBar::tab:hover {{ background: {Theme.SURFACE_LIGHT}; color: {Theme.TEXT_MAIN}; }}
        """)
        
        self.tables = {
            "extra": DiscoveryTable(),
            "image": DiscoveryTable(),
            "metadata": DiscoveryTable(),
            "subtitle": DiscoveryTable(),
            "audio": DiscoveryTable()
        }
        
        self.tabs.addTab(self._wrap_with_filter("extra", self.tables["extra"], 
            ["all", "sample", "trailer", "behind the scenes", "deleted", "interview", "featurette"]), "🎬 Bonus Videos")
        self.tabs.addTab(self._wrap_with_filter("image", self.tables["image"], 
            ["all", "poster", "fanart", "background", "banner", "thumb", "logo", "disc"]), "🖼️ Images")
        self.tabs.addTab(self.tables["metadata"], "📝 Metadata")
        self.tabs.addTab(self._wrap_with_filter("subtitle", self.tables["subtitle"], 
            ["all", "forced", "full"]), "📜 Subtitles")
        self.tabs.addTab(self._wrap_with_filter("audio", self.tables["audio"], 
            ["all", "dub", "commentary", "music"]), "🔊 Audio")
        
        layout.addWidget(self.tabs)

    def _wrap_with_filter(self, cat, table, subtypes):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        for st in subtypes:
            btn = QPushButton(st.title())
            btn.setCheckable(True)
            if st == "all": btn.setChecked(True)
            btn.setStyleSheet(self._get_chip_style())
            btn.clicked.connect(lambda checked, b=btn, c=cat, s=st: self._on_sub_filter_changed(b, c, s))
            filter_bar.addWidget(btn)
        filter_bar.addStretch()
        
        layout.addLayout(filter_bar)
        layout.addWidget(table)
        return container

    def _get_chip_style(self):
        return f"""
            QPushButton {{
                background: {Theme.SURFACE}; color: {Theme.TEXT_MUTED};
                border: 1px solid {Theme.BORDER}; border-radius: 14px;
                padding: 4px 12px; font-size: 11px; font-weight: 600;
            }}
            QPushButton:checked {{
                background: {Theme.PRIMARY}20; color: {Theme.PRIMARY};
                border-color: {Theme.PRIMARY};
            }}
            QPushButton:hover {{ border-color: {Theme.TEXT_MUTED}; }}
        """

    def _on_sub_filter_changed(self, btn, cat, subtype):
        # Uncheck others in the same bar
        parent = btn.parent()
        if parent:
            for other_btn in parent.findChildren(QPushButton):
                if other_btn != btn: other_btn.setChecked(False)
        btn.setChecked(True)
        
        self._current_sub_filters[cat] = subtype
        self.refresh()

    def fill_data(self, extra_data):
        self._raw_data = extra_data
        self.refresh()

    def refresh(self):
        split = {"extra": [], "image": [], "metadata": [], "subtitle": [], "audio": []}
        for v in self._raw_data:
            cat = v.get('category', 'unknown')
            sub = v.get('sub_category', 'all')
            
            # Apply sub-filter
            active_sub = self._current_sub_filters.get(cat, "all")
            if active_sub != "all" and sub != active_sub:
                continue
                
            if cat in split:
                split[cat].append(v)
        
        for key in split:
            self.tables[key].fill_data(split[key])
    
    def get_active_table(self):
        idx = self.tabs.currentIndex()
        mapping = {0: "extra", 1: "image", 2: "metadata", 3: "subtitle", 4: "audio"}
        return self.tables.get(mapping.get(idx))
