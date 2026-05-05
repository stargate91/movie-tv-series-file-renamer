from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PySide6.QtCore import Qt
from ui.v3.styles.theme import Theme

class BaseSettingsTab(QWidget):
    """
    Base class for settings tabs providing common UI helper methods.
    """
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine

    def _create_section_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(Theme.get_section_header_style())
        return lbl

    def _create_input_group(self, label_text, value, placeholder=""):
        group = QVBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(Theme.get_input_label_style())
        group.addWidget(lbl)
        
        edit = QLineEdit()
        edit.setText(value)
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(40)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background: {Theme.SURFACE_DARK};
                border: 1px solid {Theme.BORDER};
                border-radius: 6px;
                padding: 0 10px;
                color: {Theme.TEXT_MAIN};
            }}
            QLineEdit:disabled {{
                background: {Theme.SURFACE};
                color: {Theme.TEXT_DIM};
                border-color: {Theme.SURFACE_LIGHT};
            }}
        """)
        group.addWidget(edit)
        return {'layout': group, 'edit': edit}

    def _create_path_input(self, label_text, value, category, browse_callback):
        group = QVBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(Theme.get_input_label_style())
        group.addWidget(lbl)
        
        row = QHBoxLayout()
        edit = QLineEdit()
        edit.setText(value)
        edit.setReadOnly(True)
        edit.setFixedHeight(40)
        edit.setStyleSheet(f"background: {Theme.SURFACE_DARK}; border: 1px solid {Theme.BORDER}; border-radius: 6px; padding: 0 10px;")
        
        btn = QPushButton("Browse")
        btn.setObjectName("SecondaryButton")
        btn.setFixedSize(80, 40)
        btn.clicked.connect(lambda: browse_callback(category, edit))
        
        row.addWidget(edit)
        row.addWidget(btn)
        group.addLayout(row)
        return {'layout': group, 'edit': edit}

    def _create_tag_chips(self, tags, target_input):
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignLeft)
        
        for tag in tags:
            btn = QPushButton(tag)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(26)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Theme.SURFACE_LIGHT};
                    border: 1px solid {Theme.BORDER};
                    border-radius: 13px;
                    padding: 0 12px;
                    color: {Theme.TEXT_MAIN};
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {Theme.PRIMARY};
                    border-color: {Theme.PRIMARY};
                    color: white;
                }}
            """)
            btn.clicked.connect(lambda checked=False, t=tag, i=target_input: self._insert_tag(t, i))
            layout.addWidget(btn)
        return layout

    def _insert_tag(self, tag, target_input):
        text = f"{{{tag}}}"
        target_input.insert(text)
        target_input.setFocus()
