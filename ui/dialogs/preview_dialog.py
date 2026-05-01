from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QFrame
from PySide6.QtCore import Qt
import os

class PreviewDialog(QDialog):
    def __init__(self, parent=None, tasks=None):
        super().__init__(parent)
        self.setWindowTitle("Preview Renaming Changes")
        self.setMinimumSize(900, 600)
        
        # Allow resizing and maximize button
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        
        self.tasks = tasks or []
        # Sort tasks by new filename for better UX (Order from Chaos)
        self.tasks.sort(key=lambda x: x.new_filename.lower())
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("The following files will be processed:")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1f2328;")
        layout.addWidget(header)
        
        # Table Header
        table_header = QWidget()
        table_header.setStyleSheet("background-color: #f6f8fa; border-bottom: 1px solid #d0d7de;")
        th_layout = QHBoxLayout(table_header)
        th_layout.setContentsMargins(15, 10, 15, 10)
        
        old_h = QLabel("ORIGINAL FILENAME")
        old_h.setStyleSheet("font-weight: bold; font-size: 11px; color: #656d76;")
        new_h = QLabel("NEW FILENAME")
        new_h.setStyleSheet("font-weight: bold; font-size: 11px; color: #656d76;")
        
        th_layout.addWidget(old_h, 1)
        th_layout.addSpacing(40) # Arrow space
        th_layout.addWidget(new_h, 1)
        layout.addWidget(table_header)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(1) # Tight spacing for zebra effect
        
        for idx, task in enumerate(self.tasks):
            row = QFrame()
            # Zebra striping
            bg_color = "#ffffff" if idx % 2 == 0 else "#f6f8fa"
            row.setStyleSheet(f"background-color: {bg_color}; border-radius: 4px;")
            
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(15, 12, 15, 12)
            
            old_name = os.path.basename(task.old_path)
            new_name = task.new_filename
            
            old_lbl = QLabel(old_name)
            old_lbl.setStyleSheet("color: #656d76; font-family: 'Consolas', monospace; font-size: 12px;")
            old_lbl.setWordWrap(True)
            
            arrow_lbl = QLabel(" ➜ ")
            arrow_lbl.setStyleSheet("color: #0969da; font-weight: bold; font-size: 14px;")
            
            new_lbl = QLabel(new_name)
            new_lbl.setStyleSheet("color: #1f2328; font-weight: bold; font-family: 'Consolas', monospace; font-size: 13px;")
            new_lbl.setWordWrap(True)
            
            row_layout.addWidget(old_lbl, 1)
            row_layout.addWidget(arrow_lbl, 0)
            row_layout.addWidget(new_lbl, 1)
            
            content_layout.addWidget(row)
            
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Bottom Button
        btn_layout = QHBoxLayout()
        count_lbl = QLabel(f"Total: {len(self.tasks)} files")
        count_lbl.setStyleSheet("color: #656d76; font-style: italic;")
        
        close_btn = QPushButton("Got it")
        close_btn.setObjectName("PrimaryBtn") # Custom QSS class
        close_btn.setFixedWidth(120)
        close_btn.setFixedHeight(36)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(count_lbl)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
