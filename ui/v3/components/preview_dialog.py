from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QScrollArea, QWidget, QFrame, QLineEdit, QApplication)
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme

class PreviewDialog(QDialog):
    """A professional, searchable dialog to preview renaming operations."""
    def __init__(self, plan, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Review Renaming Plan")
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
        
        self.setStyleSheet(f"background-color: {Theme.BACKGROUND}; color: {Theme.TEXT_MAIN};")

        # Header Section
        header_layout = QHBoxLayout()
        header = QLabel(f"Rename Preview ({len(self.plan)} items)")
        header.setStyleSheet("font-size: 22px; font-weight: 800; color: white;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter files...")
        self.search_input.setFixedWidth(300)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {Theme.SURFACE_DARK};
                border: 1px solid {Theme.BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                color: white;
            }}
            QLineEdit:focus {{ border-color: {Theme.PRIMARY}; }}
        """)
        self.search_input.textChanged.connect(self._filter_items)
        header_layout.addWidget(self.search_input)
        
        layout.addLayout(header_layout)

        # Filters Section
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        self.current_filter = "All"
        self.filter_buttons = []
        
        filters = ["All", "Collision Movies", "Collision Episodes", "Ready", "Extra Collisions", "Extra Ready"]
        for f in filters:
            btn = QPushButton(f)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            if f == "All": btn.setChecked(True)
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Theme.SURFACE_DARK};
                    border: 1px solid {Theme.BORDER};
                    border-radius: 15px;
                    padding: 0 15px;
                    color: {Theme.TEXT_DIM};
                    font-weight: bold;
                    font-size: 11px;
                }}
                QPushButton:checked {{
                    background: {Theme.PRIMARY};
                    border: 1px solid {Theme.PRIMARY};
                    color: white;
                }}
            """)
            btn.clicked.connect(lambda checked, text=f: self._set_filter(text))
            self.filter_buttons.append(btn)
            filter_layout.addWidget(btn)
            
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        layout.addSpacing(10)

        # List Header
        list_header = QFrame()
        list_header.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border-bottom: 2px solid {Theme.BORDER};")
        lh_layout = QHBoxLayout(list_header)
        lh_layout.setContentsMargins(20, 10, 20, 10)
        
        l_old = QLabel("CURRENT FILENAME")
        l_new = QLabel("PROPOSED FILENAME")
        for l in [l_old, l_new]:
            l.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {Theme.TEXT_DIM}; letter-spacing: 1px;")
        
        lh_layout.addWidget(l_old, 4)
        lh_layout.addSpacing(40)
        lh_layout.addWidget(l_new, 6)
        layout.addWidget(list_header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(f"background-color: transparent;")
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
            if not p: return "DELETED"
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
            
            item_frame.setStyleSheet(f"""
                QFrame#Row {{ 
                    background-color: {bg_color}; 
                    border-bottom: 1px solid {border_color};
                }}
                QFrame#Row:hover {{ background-color: {Theme.SURFACE_LIGHT if not is_collision else "rgba(239, 68, 68, 0.1)"}; }}
            """)
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(20, 15, 20, 15)
            item_layout.setSpacing(20)
            
            old_name = os.path.basename(item['original_path'])
            new_name = shorten_path(item['proposed_path']) if item['proposed_path'] else "DELETED"
            
            # Use basename for the QLineEdit so they don't have to retype folders
            new_basename = os.path.basename(item['proposed_path']) if item['proposed_path'] else ""
            
            # Left Side (Old)
            old_lbl = QLabel(old_name)
            old_lbl.setWordWrap(True)
            old_lbl.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-family: monospace; font-size: 12px;")
            item_layout.addWidget(old_lbl, 4)
            
            # Center Arrow
            arrow = QLabel(" → ")
            arrow.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: 900; font-size: 16px;")
            item_layout.addWidget(arrow)
            
            # Right Side (New)
            if is_collision:
                resolve_layout = QHBoxLayout()
                resolve_layout.setSpacing(5)
                edit = QLineEdit(new_basename)
                edit.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border: 1px solid {Theme.BORDER}; color: {Theme.TEXT_MAIN}; padding: 4px; font-family: monospace;")
                
                # Up / Down buttons for reordering within the collision group
                btn_up = QPushButton("▲")
                btn_up.setCursor(Qt.PointingHandCursor)
                btn_up.setFixedSize(24, 24)
                btn_up.setStyleSheet(f"background: {Theme.SURFACE_LIGHT}; color: white; border-radius: 4px; font-size: 10px;")
                btn_up.clicked.connect(lambda checked=False, idx=i: self._reorder_collision(idx, -1))
                
                btn_down = QPushButton("▼")
                btn_down.setCursor(Qt.PointingHandCursor)
                btn_down.setFixedSize(24, 24)
                btn_down.setStyleSheet(f"background: {Theme.SURFACE_LIGHT}; color: white; border-radius: 4px; font-size: 10px;")
                btn_down.clicked.connect(lambda checked=False, idx=i: self._reorder_collision(idx, 1))
                
                btn = QPushButton("Manual")
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(f"background: {Theme.PRIMARY}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
                btn.clicked.connect(lambda checked=False, idx=i, e=edit: self._resolve_collision(idx, e.text()))
                
                btn_auto = QPushButton("Auto-Part")
                btn_auto.setCursor(Qt.PointingHandCursor)
                btn_auto.setToolTip("Automatically append Part 1, Part 2, etc. to all conflicting files with this name.")
                btn_auto.setStyleSheet(f"background: {Theme.WARNING}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
                btn_auto.clicked.connect(lambda checked=False, p=item['proposed_path']: self._auto_part_group(p))
                
                if item.get('category', 'video') != 'video':
                    btn_auto.setEnabled(False)
                    btn_auto.setToolTip("Auto-Part is only available for video files.")
                    btn_auto.setStyleSheet(f"background: {Theme.SURFACE_LIGHT}; color: {Theme.TEXT_DIM}; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
                    
                resolve_layout.addWidget(btn_up)
                resolve_layout.addWidget(btn_down)
                resolve_layout.addWidget(edit, 1)
                resolve_layout.addWidget(btn)
                resolve_layout.addWidget(btn_auto)
                item_layout.addLayout(resolve_layout, 6)
            else:
                color = Theme.SUCCESS if item['action'] == 'rename' else Theme.ERROR
                new_lbl = QLabel(new_name)
                new_lbl.setWordWrap(True)
                new_lbl.setStyleSheet(f"color: {color}; font-family: monospace; font-size: 13px; font-weight: 700;")
                item_layout.addWidget(new_lbl, 6)
            
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
        summary_text = f"Plan: {len([p for p in self.plan if p['action']=='rename'])} Renames, {len([p for p in self.plan if p['action']=='delete'])} Deletions"
        if self.collision_count > 0:
            summary_text += f" | <b style='color: {Theme.ERROR};'>{self.collision_count} COLLISIONS DETECTED</b>"
            
        summary = QLabel(summary_text)
        summary.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-size: 13px;")
        footer_top.addWidget(summary)
        footer_top.addStretch()
        self.footer_layout.addLayout(footer_top)

        footer_btns = QHBoxLayout()
        footer_btns.setContentsMargins(0, 10, 0, 0)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(140, 45)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {Theme.BORDER};
                color: {Theme.TEXT_MAIN};
                border-radius: 8px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Theme.SURFACE_LIGHT}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        apply_btn = QPushButton("Execute Changes")
        apply_btn.setFixedSize(220, 45)
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.setStyleSheet(Theme.get_primary_button_style())
        apply_btn.clicked.connect(self.accept)
        
        if self.collision_count > 0:
            apply_btn.setEnabled(False)
            apply_btn.setToolTip("Please resolve collisions before executing.")
        
        footer_btns.addStretch()
        footer_btns.addWidget(cancel_btn)
        footer_btns.addWidget(apply_btn)
        self.footer_layout.addLayout(footer_btns)

    def _resolve_collision(self, idx, new_filename):
        import os
        item = self.plan[idx]
        if not item['proposed_path']: return
        
        dir_name = os.path.dirname(item['proposed_path'])
        item['proposed_path'] = os.path.join(dir_name, new_filename)
        
        self._recheck_collisions()

    def _reorder_collision(self, idx, direction):
        """Moves an item up (-1) or down (1) within its collision group."""
        item = self.plan[idx]
        proposed = item.get('proposed_path', '').lower()
        if not proposed: return
        
        # Find all indices in self.plan that share this proposed path
        group_indices = [i for i, p in enumerate(self.plan) if p.get('proposed_path', '').lower() == proposed]
        
        try:
            group_pos = group_indices.index(idx)
        except ValueError:
            return
            
        target_pos = group_pos + direction
        if 0 <= target_pos < len(group_indices):
            # Swap in self.plan
            target_idx = group_indices[target_pos]
            self.plan[idx], self.plan[target_idx] = self.plan[target_idx], self.plan[idx]
            
            # Rebuild UI
            self._build_list()

    def _auto_part_group(self, proposed_path):
        # Find all items colliding on this path
        group = [item for item in self.plan if item.get('proposed_path', '').lower() == proposed_path.lower()]
        
        if len(group) > 1 and self.parent() and hasattr(self.parent(), 'engine'):
            resolver = self.parent().engine.collision_resolver
            resolver.force_resolve_group(group)
            self._recheck_collisions()

    def _recheck_collisions(self):
        # Build path map to find duplicates
        path_map = {}
        for item in self.plan:
            if item['action'] == 'skip' or not item['proposed_path']: continue
            path = item['proposed_path'].lower()
            if path not in path_map: path_map[path] = []
            path_map[path].append(item)
            
        # Update statuses
        for path, items in path_map.items():
            if len(items) > 1:
                for p in items: p['status'] = 'collision'
            else:
                for p in items: p['status'] = 'manual_resolved' # or safe
                
        # Rebuild UI
        self._build_list()

    def _set_filter(self, text):
        self.current_filter = text
        for btn in self.filter_buttons:
            if btn.text() != text:
                btn.setChecked(False)
            else:
                btn.setChecked(True)
        self._filter_items(self.search_input.text())

    def _filter_items(self, text):
        query = text.lower()
        
        container = self.scroll.widget()
        if container:
            container.setUpdatesEnabled(False)
            container.layout().setEnabled(False)
            
        for widget, item, old, new in self.item_widgets:
            matches_text = query in old or query in new
            
            status = item.get('status', 'safe')
            is_collision = status == 'collision'
            cat = item.get('category', 'video')
            media_type = item.get('media_type', 'unknown')
            
            matches_filter = True
            if self.current_filter == "Collision Movies":
                matches_filter = is_collision and cat == 'video' and media_type == 'movie'
            elif self.current_filter == "Collision Episodes":
                matches_filter = is_collision and cat == 'video' and media_type == 'episode'
            elif self.current_filter == "Ready":
                matches_filter = not is_collision and cat == 'video'
            elif self.current_filter == "Extra Collisions":
                matches_filter = is_collision and cat != 'video'
            elif self.current_filter == "Extra Ready":
                matches_filter = not is_collision and cat != 'video'
                
            widget.setVisible(matches_text and matches_filter)
            
        if container:
            container.layout().setEnabled(True)
            container.setUpdatesEnabled(True)
