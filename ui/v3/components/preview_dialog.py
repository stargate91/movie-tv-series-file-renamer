from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QScrollArea, QWidget, QFrame, QLineEdit, QApplication)
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from core.i18n import T

class PreviewDialog(QDialog):
    """A professional, searchable dialog to preview renaming operations."""
    def __init__(self, plan, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("preview.title"))
        self.setMinimumSize(1000, 700)
        # Enable maximize and minimize buttons
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.plan = plan
        self.item_widgets = [] # Store for filtering
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        self.setStyleSheet(Theme.get_preview_dialog_style())

        # Header Section
        header_layout = QHBoxLayout()
        header = QLabel(T("preview.header", count=len(self.plan)))
        header.setStyleSheet(Theme.get_preview_header_style())
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("preview.filter_placeholder"))
        self.search_input.setFixedWidth(350)
        self.search_input.setStyleSheet(Theme.get_preview_search_input_style())
        self.search_input.textChanged.connect(self._filter_items)
        header_layout.addWidget(self.search_input)
        
        layout.addLayout(header_layout)
        layout.addSpacing(10)

        # List Header
        list_header = QFrame()
        list_header.setStyleSheet(Theme.get_preview_list_header_style())
        lh_layout = QHBoxLayout(list_header)
        lh_layout.setContentsMargins(20, 10, 20, 10)
        
        l_old = QLabel(T("preview.col_current"))
        l_new = QLabel(T("preview.col_proposed"))
        for l in [l_old, l_new]:
            l.setStyleSheet(Theme.get_preview_col_label_style())
        
        lh_layout.addWidget(l_old, 4)
        lh_layout.addSpacing(40)
        lh_layout.addWidget(l_new, 6)
        layout.addWidget(list_header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(Theme.get_scroll_area_style())
        self.scroll.verticalScrollBar().setStyleSheet(Theme.get_scrollbar_style())
        layout.addWidget(self.scroll)

        # Footer container
        self.footer_container = QWidget()
        self.footer_layout = QVBoxLayout(self.footer_container)
        self.footer_layout.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(self.footer_container)

        self._build_list()

    def _build_list(self):
        import os
        
        # Determine roots for relative paths
        roots = []
        if self.parent() and hasattr(self.parent(), 'engine'):
            s = self.parent().engine.config.settings
            if s.move_files and s.base_target_path:
                base = os.path.normpath(s.base_target_path)
                roots.append(base)
                if s.auto_organize_by_type:
                    if s.movies_subfolder_name: roots.append(os.path.join(base, s.movies_subfolder_name))
                    if s.shows_subfolder_name: roots.append(os.path.join(base, s.shows_subfolder_name))
            
        orig_paths = [item['original_path'] for item in self.plan if item.get('original_path')]
        if orig_paths:
            common = os.path.commonpath(orig_paths)
            if os.path.isfile(common): common = os.path.dirname(common)
            roots.append(os.path.normpath(common))
            
        def is_subdir(path, directory):
            try:
                rel = os.path.relpath(path, directory)
                return not rel.startswith('..') and not os.path.isabs(rel)
            except ValueError:
                return False

        def shorten_path(p):
            if not p: return T("preview.deleted")
            p_norm = os.path.normpath(p)
            best_root = None
            for r in roots:
                if is_subdir(p_norm, r):
                    if best_root is None or len(r) > len(best_root):
                        best_root = r
            if best_root:
                return os.path.relpath(p_norm, best_root).replace('\\', '/')
            parts = p_norm.replace('\\', '/').split('/')
            return "/".join(parts[-2:]) if len(parts) >= 2 else os.path.basename(p_norm)

        # Clear existing
        self.item_widgets = []
        if self.scroll.widget():
            self.scroll.widget().deleteLater()
            
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(1)
        container_layout.setAlignment(Qt.AlignTop)

        self.collision_count = 0
        for i, item in enumerate(self.plan):
            status = item.get('status', 'safe')
            is_collision = status == 'collision'
            if is_collision: self.collision_count += 1

            item_frame = QFrame()
            item_frame.setObjectName("Row")
            bg_color = "rgba(239, 68, 68, 0.05)" if is_collision else Theme.SURFACE
            border_color = Theme.ERROR if is_collision else Theme.BORDER
            
            item_frame.setStyleSheet(Theme.get_preview_row_style(is_collision=is_collision))
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(20, 15, 20, 15)
            item_layout.setSpacing(20)
            
            old_name = os.path.basename(item['original_path'])
            new_name = shorten_path(item['proposed_path']) if item['proposed_path'] else T("preview.deleted")
            
            # Use basename for the QLineEdit so they don't have to retype folders
            new_basename = os.path.basename(item['proposed_path']) if item['proposed_path'] else ""
            
            # Left Side (Old)
            old_lbl = QLabel(old_name)
            old_lbl.setWordWrap(True)
            old_lbl.setStyleSheet(Theme.get_preview_old_name_style())
            item_layout.addWidget(old_lbl, 4)
            
            # Center Arrow
            arrow = QLabel(" → ")
            arrow.setStyleSheet(Theme.get_preview_arrow_style())
            item_layout.addWidget(arrow)
            
            # Right Side (New)
            color = Theme.SUCCESS if item['action'] == 'rename' else Theme.ERROR
            new_lbl = QLabel(new_name)
            new_lbl.setWordWrap(True)
            new_lbl.setStyleSheet(Theme.get_preview_new_name_style(color=color))
            item_layout.addWidget(new_lbl, 6)
                
            # Add a global Remove button to the far right for EVERY item
            btn_remove = QPushButton()
            btn_remove.setIcon(Theme.get_icon("trash-2", size=16, color=Theme.ERROR))
            btn_remove.setCursor(Qt.PointingHandCursor)
            btn_remove.setFixedSize(28, 28)
            btn_remove.setToolTip(T("preview.remove_tooltip"))
            btn_remove.setStyleSheet(Theme.get_preview_remove_btn_style())
            btn_remove.clicked.connect(lambda checked=False, p_item=item: self._remove_item(p_item))
            item_layout.addWidget(btn_remove)
            
            container_layout.addWidget(item_frame)
            self.item_widgets.append((item_frame, item, old_name.lower(), new_name.lower()))

        self.scroll.setWidget(container)
        self._build_footer()
        # Ensure the filter is applied to the newly built list
        self._filter_items(self.search_input.text())
        
    def _build_footer(self):
        # Clear existing footer
        while self.footer_layout.count():
            item = self.footer_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    subitem = item.layout().takeAt(0)
                    if subitem.widget(): subitem.widget().deleteLater()
                item.layout().deleteLater()

        footer_top = QHBoxLayout()
        renames = len([p for p in self.plan if p['action']=='rename'])
        deletions = len([p for p in self.plan if p['action']=='delete'])
        
        summary_text = T("preview.summary", renames=renames, deletions=deletions)
        if self.collision_count > 0:
            summary_text += f" | <b style='color: {Theme.ERROR};'>{T('discovery.messages.collision_detected', count=self.collision_count)}</b>"
            
        summary = QLabel(summary_text)
        summary.setStyleSheet(Theme.get_preview_summary_style())
        footer_top.addWidget(summary)
        footer_top.addStretch()
        self.footer_layout.addLayout(footer_top)

        footer_btns = QHBoxLayout()
        footer_btns.setContentsMargins(0, 10, 0, 0)
        
        cancel_btn = QPushButton(T("common.cancel"))
        cancel_btn.setFixedSize(140, 45)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(Theme.get_preview_cancel_btn_style())
        cancel_btn.clicked.connect(self.reject)
        
        apply_btn = QPushButton(T("preview.execute"))
        apply_btn.setFixedSize(220, 45)
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.setStyleSheet(Theme.get_primary_button_style())
        apply_btn.clicked.connect(self.accept)
        
        if self.collision_count > 0:
            apply_btn.setEnabled(False)
            apply_btn.setToolTip(T("discovery.messages.collision_tooltip"))
        
        footer_btns.addStretch()
        footer_btns.addWidget(cancel_btn)
        footer_btns.addWidget(apply_btn)
        self.footer_layout.addLayout(footer_btns)

    def _remove_item(self, item):
        """Removes an item completely from the plan."""
        try:
            self.plan.remove(item)
            self._build_list()
        except ValueError:
            pass

    def _filter_items(self, text):
        query = text.lower()
        
        container = self.scroll.widget()
        if container:
            container.setUpdatesEnabled(False)
            container.layout().setEnabled(False)
            
        for widget, item, old, new in self.item_widgets:
            matches_text = query in old or query in new
            widget.setVisible(matches_text)
            
        if container:
            container.layout().setEnabled(True)
            container.setUpdatesEnabled(True)
