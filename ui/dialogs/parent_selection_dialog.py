from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QLineEdit, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
import os

class ParentSelectionDialog(QDialog):
    def __init__(self, parent, main_files):
        super().__init__(parent)
        self.setWindowTitle("Link to Parent Feature")
        self.setMinimumSize(400, 500)
        self.selected_parent = None
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the main video this extra belongs to:"))
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter files...")
        self.search.textChanged.connect(self.filter_list)
        layout.addWidget(self.search)
        
        self.list = QListWidget()
        self.main_files = sorted(main_files)
        for f in self.main_files:
            self.list.addItem(os.path.basename(f))
            self.list.item(self.list.count()-1).setData(Qt.UserRole, f)
            
        self.list.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.list)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Link File")
        ok_btn.setObjectName("PrimaryBtn")
        ok_btn.clicked.connect(self.accept_selection)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def filter_list(self, text):
        text = text.lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(text not in item.text().lower())

    def accept_selection(self):
        curr = self.list.currentItem()
        if curr:
            self.selected_parent = curr.data(Qt.UserRole)
            self.accept()
