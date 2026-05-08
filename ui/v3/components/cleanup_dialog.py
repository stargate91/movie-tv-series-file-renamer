import os
import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox)
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme
from core.i18n import T

logger = logging.getLogger(__name__)

class CleanupDialog(QDialog):
    """
    Dialog to handle leftovers after a rename/move operation.
    Displays remaining files in non-empty directories and offers to trash them.
    """
    def __init__(self, parent, leftovers, engine):
        super().__init__(parent)
        self.leftovers = leftovers
        self.engine = engine
        self.setWindowTitle(T("cleanup.title"))
        self.setMinimumSize(600, 400)
        self.setStyleSheet(Theme.get_main_stylesheet())
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        total_dirs = len(self.leftovers)
        total_files = sum(len(files) for files in self.leftovers.values())
        
        header_lbl = QLabel(T("cleanup.header", dirs=total_dirs, files=total_files))
        header_lbl.setWordWrap(True)
        header_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #E0E0E0;")
        layout.addWidget(header_lbl)

        # Tree View for leftovers
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet(Theme.get_sidebar_tree_style())
        
        for dir_path, files in self.leftovers.items():
            dir_item = QTreeWidgetItem(self.tree, [os.path.basename(dir_path)])
            dir_item.setToolTip(0, dir_path)
            dir_item.setExpanded(True)
            
            for f in files:
                file_item = QTreeWidgetItem(dir_item, [f])
                file_item.setToolTip(0, os.path.join(dir_path, f))

        layout.addWidget(self.tree)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_leave = QPushButton(T("cleanup.btn_leave"))
        self.btn_leave.setStyleSheet(Theme.get_secondary_button_style())
        self.btn_leave.clicked.connect(self.reject)
        
        self.btn_delete = QPushButton(T("cleanup.btn_delete"))
        self.btn_delete.setStyleSheet(Theme.get_danger_button_style())
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_leave)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

    def _on_delete_clicked(self):
        try:
            import send2trash
        except ImportError:
            QMessageBox.critical(self, T("common.error"), "send2trash module not found! Please install it: pip install send2trash")
            return

        reply = QMessageBox.question(
            self, T("cleanup.confirm_title"),
            T("cleanup.confirm_msg"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        success_count = 0
        error_count = 0
        
        for dir_path, files in self.leftovers.items():
            # 1. Törlés az adatbázisból
            try:
                self.engine.db.files.delete_by_path_prefix(dir_path)
            except Exception as e:
                logger.error(f"Failed to clean DB for {dir_path}: {e}")

            # 2. Fizikai törlés a Lomtárba
            try:
                send2trash.send2trash(dir_path)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to trash {dir_path}: {e}")
                error_count += 1

        if error_count > 0:
            QMessageBox.warning(self, T("history.undo_partial_title"), T("cleanup.partial_success", success=success_count, failed=error_count))
        else:
            QMessageBox.information(self, T("cleanup.done_title"), T("cleanup.done_msg"))
            
        self.accept()
