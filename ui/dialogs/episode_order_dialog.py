import os
import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QAbstractItemView, QListWidgetItem, QLabel, QSpinBox
)
from PySide6.QtCore import Qt

class EpisodeOrderDialog(QDialog):
    def __init__(self, parent, paths, default_start=1):
        super().__init__(parent)
        self.setWindowTitle("🪄 Sequence Episodes Wizard")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.paths_map = {} # basename -> fullpath
        
        layout = QVBoxLayout(self)
        
        # Top Config Area
        config_layout = QHBoxLayout()
        start_lbl = QLabel("<b>Start numbering from Episode:</b>")
        start_lbl.setStyleSheet("color: #1a1a2e; font-size: 13px;")
        self.start_spinbox = QSpinBox()
        self.start_spinbox.setMinimum(1)
        self.start_spinbox.setMaximum(9999)
        self.start_spinbox.setValue(default_start)
        self.start_spinbox.valueChanged.connect(self.update_list_labels)
        
        config_layout.addWidget(start_lbl)
        config_layout.addWidget(self.start_spinbox)
        config_layout.addStretch()
        layout.addLayout(config_layout)
        
        info = QLabel("Drag and drop items to fix the order if needed.")
        info.setStyleSheet("color: #6b7280; font-size: 11px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #d6dce5;
                border-radius: 4px;
                background-color: #ffffff;
                font-size: 13px;
                color: #1a1a2e;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e5f1fb;
                color: #000000;
            }
        """)
        
        # Natural sort helper
        def natural_keys(text):
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]
            
        # Initially sort naturally so 10 comes after 2
        sorted_paths = sorted(paths, key=lambda x: natural_keys(os.path.basename(x)))
        
        for p in sorted_paths:
            basename = os.path.basename(p)
            self.paths_map[basename] = p
            item = QListWidgetItem()
            # Store basename in UserRole for easy retrieval
            item.setData(Qt.UserRole, basename)
            self.list_widget.addItem(item)
            
        self.list_widget.model().rowsMoved.connect(self.update_list_labels)
        self.update_list_labels()
        
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.apply_btn = QPushButton("✅ Apply Sequence")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.setStyleSheet("background-color: #0078d4; color: white; border: none; padding: 6px 16px; border-radius: 4px; font-weight: bold;")
        self.apply_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.apply_btn)
        layout.addLayout(btn_layout)

    def update_list_labels(self, *args):
        start_num = self.start_spinbox.value()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            basename = item.data(Qt.UserRole)
            item.setText(f"⠿  E{start_num + i:02d}  →  {basename}")

    def get_results(self):
        ordered = []
        for i in range(self.list_widget.count()):
            basename = self.list_widget.item(i).data(Qt.UserRole)
            ordered.append(self.paths_map[basename])
        return ordered, self.start_spinbox.value()
