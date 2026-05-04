import os
import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox)
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme

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
        self.setWindowTitle("Cleanup Leftovers")
        self.setMinimumSize(600, 400)
        self.setStyleSheet(Theme.get_main_stylesheet())
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        total_dirs = len(self.leftovers)
        total_files = sum(len(files) for files in self.leftovers.values())
        
        header_lbl = QLabel(f"Rename successful! Left with {total_dirs} folder(s) containing a total of {total_files} potentially unnecessary file(s).")
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
        
        self.btn_leave = QPushButton("Leave them be")
        self.btn_leave.setStyleSheet(Theme.get_secondary_button_style())
        self.btn_leave.clicked.connect(self.reject)
        
        self.btn_delete = QPushButton("Move to Recycle Bin")
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
            QMessageBox.critical(self, "Error", "send2trash module not found! Please install it: pip install send2trash")
            return

        reply = QMessageBox.question(
            self, 'Confirm',
            "Are you sure you want to move these folders and all their contents to the Recycle Bin?\n\nThis will also remove the affected files from the database.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        success_count = 0
        error_count = 0
        
        for dir_path, files in self.leftovers.items():
            # 1. Törlés az adatbázisból
            try:
                conn = self.engine.db._get_connection()
                # Törlünk minden olyan rekordot, ami ebben a mappában van
                like_pattern = f"{dir_path}{os.sep}%"
                conn.execute("DELETE FROM media_files WHERE current_path LIKE ?", (like_pattern,))
                # És ha pont maga a mappa lenne (bár mappákat nem tárolunk media_files-ként)
                conn.execute("DELETE FROM media_files WHERE current_path = ?", (dir_path,))
                conn.commit()
                conn.close()
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
            QMessageBox.warning(self, "Partial Success", f"Deleted {success_count} folders, {error_count} failed.")
        else:
            QMessageBox.information(self, "Done", "The leftover items have been moved to the Recycle Bin!")
            
        self.accept()
