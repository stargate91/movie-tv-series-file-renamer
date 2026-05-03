import os
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QCheckBox
from PySide6.QtCore import Qt, Signal
from ui.widgets.image_widgets import ImageLoader
from ui.widgets.buttons import SecondaryButton
from ui.dialogs.metadata_dialog import MetadataDialog
from ui.styles import UIStyles

class MovieCard(QFrame):
    selection_changed = Signal(bool) # Signal to notify MainWindow
    
    def __init__(self, file_path, meta, pipeline, on_click, on_edit, on_remove=None):
        super().__init__()
        self.setObjectName("Card")
        self.setMinimumHeight(90)
        self.file_path = file_path
        self.meta = meta
        self.pipeline = pipeline
        self.on_click_cb = on_click
        self.on_edit_cb = on_edit
        self.on_remove_cb = on_remove
        
        status = meta.get('status', 'pending') if meta else 'pending'
        is_extra = meta and (meta.get('file_type') == 'extra' or status == 'extra')
        
        self.setStyleSheet(UIStyles.get_card_style(is_extra=is_extra))
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 15, 10)
        layout.setSpacing(15)
        
        self.checkbox = QCheckBox()
        self.checkbox.setFixedWidth(30)
        self.checkbox.toggled.connect(self.selection_changed.emit)
        layout.addWidget(self.checkbox, 0, Qt.AlignVCenter)
        
        # Status Icon/Indicator
        is_manual = meta.get('is_manual', False) if meta else False
        # Windows semantic colors
        color = "#10b981" if status == 'one_match' else "#f59e0b" if status == 'multi_match' else "#ef4444" if status == 'no_match' else "#94a3b8"
        if is_manual: color = "#0078d4"
        
        indicator = QFrame()
        indicator.setFixedSize(10, 10)
        indicator.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        layout.addWidget(indicator, 0, Qt.AlignVCenter)
        
        # Poster (Hidden for Extras)
        poster_url = None
        is_episode = meta.get('file_type') == 'episode' and status not in ['pending', 'extra'] if meta else False
        
        if not is_extra:
            if meta and status == 'one_match':
                p_path = meta.get('details', {}).get('poster_path') or meta.get('details', {}).get('still_path')
                if p_path:
                    poster_url = f"https://image.tmdb.org/t/p/w200{p_path}"
            
            width = 100 if is_episode else 40
            self.poster = ImageLoader(poster_url, width=width, height=60)
            layout.addWidget(self.poster, 0, Qt.AlignVCenter)
        else:
            layout.addSpacing(10) 
            
        # Text Info
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignVCenter)
        info_layout.setSpacing(2)
        if meta and status == 'one_match':
            d = meta.get('details', {})
            is_ep = meta.get('file_type') == 'episode'
            
            if is_ep:
                title_text = f"{d.get('episode_title') or d.get('name') or 'Unknown Episode'}"
                subtitle_text = d.get('series_title') or d.get('series_name') or ""
                year_val = (d.get('air_date', ''))[:4]
            else:
                title_text = f"{d.get('title') or d.get('name') or 'Unknown Title'}"
                subtitle_text = ""
                year_val = (d.get('release_date') or d.get('first_air_date', ''))[:4]
            
            if year_val and year_val != 'Unkn': title_text += f" ({year_val})"
            
            title_lbl = QLabel(title_text)
            title_lbl.setStyleSheet("font-weight: 700; font-size: 14px; color: #0f172a;")
            info_layout.addWidget(title_lbl)

            if subtitle_text and subtitle_text != "Unknown Series":
                sub_lbl = QLabel(subtitle_text)
                sub_lbl.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 500;")
                info_layout.addWidget(sub_lbl)
        else:
            title_lbl = QLabel(os.path.basename(file_path))
            title_lbl.setStyleSheet("font-weight: 700; font-size: 14px; color: #0f172a;")
            info_layout.addWidget(title_lbl)

        # Extra Metadata for Extras
        if is_extra:
            parent = meta.get('extra_parent')
            if parent:
                parent_lbl = QLabel(f"🔗 Linked to: {parent}")
                parent_lbl.setStyleSheet("font-size: 11px; color: #6366f1; font-style: italic;")
                info_layout.addWidget(parent_lbl)
                
                # Add Preview text for Extra
                from core.renamer import get_preview_name
                formatted = get_preview_name(self.file_path, meta, self.pipeline.s, self.pipeline.metadata_map)
                ext = os.path.splitext(self.file_path)[1]
                
                preview_lbl = QLabel(f"➔ {formatted}{ext}")
                preview_lbl.setStyleSheet("font-size: 11px; color: #059669; font-weight: bold;")
                info_layout.addWidget(preview_lbl)
            
        file_lbl = QLabel(os.path.basename(file_path))
        file_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
        info_layout.addWidget(file_lbl)
        
        layout.addLayout(info_layout, 1)
        
        # Actions
        actions_row = QHBoxLayout()
        actions_row.setSpacing(5)
        
        # --- Multi-part / Group UI ---
        from PySide6.QtWidgets import QLineEdit
        from PySide6.QtGui import QIntValidator
        
        self.part_group_container = QWidget()
        part_layout = QHBoxLayout(self.part_group_container)
        part_layout.setContentsMargins(0, 0, 0, 0)
        part_layout.setSpacing(5)
        
        self.part_badge = QLabel("PART")
        self.part_badge.setStyleSheet("""
            background-color: #6366f1; color: white; border-radius: 10px; 
            padding: 2px 8px; font-weight: bold; font-size: 10px;
        """)
        part_layout.addWidget(self.part_badge)
        
        self.part_input = QLineEdit()
        self.part_input.setFixedWidth(40)
        self.part_input.setFixedHeight(24)
        self.part_input.setValidator(QIntValidator(1, 99))
        self.part_input.setAlignment(Qt.AlignCenter)
        self.part_input.setStyleSheet("""
            QLineEdit { 
                border: 1px solid #e2e8f0; border-radius: 4px; background: white; 
                font-size: 12px; font-weight: bold;
            }
            QLineEdit:focus { border-color: #6366f1; }
        """)
        self.part_input.textChanged.connect(self._on_part_changed)
        part_layout.addWidget(self.part_input)
        
        self.part_group_container.setVisible(False)
        actions_row.addWidget(self.part_group_container)
        
        self.info_btn = QPushButton("ⓘ")
        self.info_btn.setToolTip("Metadata Details")
        self.info_btn.setFixedSize(30, 30)
        self.info_btn.setStyleSheet("""
            QPushButton { 
                background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; 
                border-radius: 15px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background: #e2e8f0; color: #0078d4; border-color: #cbd5e1; }
        """)
        self.info_btn.clicked.connect(self.on_info_clicked)
        actions_row.addWidget(self.info_btn)

        self.edit_btn = SecondaryButton("Edit")
        self.edit_btn.clicked.connect(lambda: self.on_edit_cb(None))
        actions_row.addWidget(self.edit_btn)
        
        # Hide buttons if pending (No analysis yet)
        if status == 'pending':
            self.edit_btn.setVisible(False)
            self.info_btn.setVisible(False)
        
        layout.addLayout(actions_row)
        
        if on_remove:
            self.remove_btn = QPushButton("✕")
            self.remove_btn.setFixedSize(30, 30)
            self.remove_btn.setStyleSheet("border: none; color: #ef4444; font-size: 18px; font-weight: bold;")
            self.remove_btn.clicked.connect(lambda: on_remove(None))
            layout.addWidget(self.remove_btn)

    def set_group_mode(self, number, badge_text):
        """Called by the list manager if this card is part of a collision group."""
        if number is not None:
            self.part_group_container.setVisible(True)
            self.part_input.setText(str(number))
            self.part_badge.setText(badge_text)
        else:
            self.part_group_container.setVisible(False)

    def _on_part_changed(self, text):
        if not text: return
        try:
            num = int(text)
            # Update the badge based on current global settings
            from ui.managers.list_manager import MediaListManager
            # We can't easily reach back to list manager here, 
            # so we let the list manager handle the signal if needed
            # For now, just update the local badge if we can guess the keyword
            keyword = self.pipeline.s.multi_part_keyword if self.pipeline.s.multi_part_keyword != "None" else ""
            self.part_badge.setText(f"{keyword}{num}")
            
            # Notify state so it persists
            self.pipeline.state.metadata_map[self.file_path]['part'] = num
        except: pass

    def on_info_clicked(self):
        from ui.dialogs.metadata_dialog import MetadataDialog
        dialog = MetadataDialog(self.window(), self.file_path, self.meta)
        dialog.exec()

    def set_active(self, active):
        is_extra = self.meta and (self.meta.get('file_type') == 'extra' or self.meta.get('status') == 'extra')
        self.setStyleSheet(UIStyles.get_card_style(is_extra=is_extra, is_active=active))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_click_cb(None)
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_edit_cb(None)
            super().mouseDoubleClickEvent(event)
