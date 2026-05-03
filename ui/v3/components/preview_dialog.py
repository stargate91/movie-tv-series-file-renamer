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

        # List Header
        list_header = QFrame()
        list_header.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border-bottom: 2px solid {Theme.BORDER};")
        lh_layout = QHBoxLayout(list_header)
        lh_layout.setContentsMargins(20, 10, 20, 10)
        
        l_old = QLabel("CURRENT FILENAME")
        l_new = QLabel("PROPOSED FILENAME")
        for l in [l_old, l_new]:
            l.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {Theme.TEXT_DIM}; letter-spacing: 1px;")
        
        lh_layout.addWidget(l_old, 1)
        lh_layout.addSpacing(40)
        lh_layout.addWidget(l_new, 1)
        layout.addWidget(list_header)

        # Scroll Area for the list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background-color: transparent;")
        scroll.verticalScrollBar().setStyleSheet(Theme.get_scrollbar_style())
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(1) # Tight list
        self.container_layout.setAlignment(Qt.AlignTop)

        import os
        self.collision_count = 0
        for item in self.plan:
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
            new_name = os.path.basename(item['proposed_path']) if item['proposed_path'] else "DELETED"
            
            # Left Side (Old)
            old_lbl = QLabel(old_name)
            old_lbl.setWordWrap(True)
            old_lbl.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-family: monospace; font-size: 12px;")
            
            # Center Arrow
            arrow = QLabel(" → ")
            arrow.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: 900; font-size: 16px;")
            
            # Right Side (New)
            new_lbl = QLabel(new_name)
            new_lbl.setWordWrap(True)
            
            if is_collision:
                color = Theme.ERROR
                new_lbl.setText(f"{new_name} [COLLISION]")
            else:
                color = Theme.SUCCESS if item['action'] == 'rename' else Theme.ERROR
                
            new_lbl.setStyleSheet(f"color: {color}; font-family: monospace; font-size: 13px; font-weight: 700;")
            
            item_layout.addWidget(old_lbl, 1)
            item_layout.addWidget(arrow)
            item_layout.addWidget(new_lbl, 1)
            
            self.container_layout.addWidget(item_frame)
            self.item_widgets.append((item_frame, old_name.lower(), new_name.lower()))

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Footer with summary and buttons
        footer_layout = QVBoxLayout()
        
        footer_top = QHBoxLayout()
        summary_text = f"Plan: {len([p for p in self.plan if p['action']=='rename'])} Renames, {len([p for p in self.plan if p['action']=='delete'])} Deletions"
        if self.collision_count > 0:
            summary_text += f" | <b style='color: {Theme.ERROR};'>{self.collision_count} COLLISIONS DETECTED</b>"
            
        summary = QLabel(summary_text)
        summary.setStyleSheet(f"color: {Theme.TEXT_DIM}; font-size: 13px;")
        footer_top.addWidget(summary)
        footer_top.addStretch()
        footer_layout.addLayout(footer_top)

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
        footer_layout.addLayout(footer_btns)
        
        layout.addLayout(footer_layout)

    def _filter_items(self, text):
        query = text.lower()
        for widget, old, new in self.item_widgets:
            visible = query in old or query in new
            widget.setVisible(visible)
