from PySide6.QtWidgets import QFrame

class Theme:
    # --- Dark Mode Palette (Premium Slate/Indigo) ---
    PRIMARY = "#3B82F6"       # Bright Blue (Blue 500)
    PRIMARY_HOVER = "#60A5FA" # Lighter Blue (Blue 400)
    
    BACKGROUND = "#0F172A"    # Deep Navy (Slate 900)
    SURFACE = "#1E293B"       # Dark Slate (Slate 800)
    SURFACE_DARK = "#020617"  # Almost Black
    SURFACE_LIGHT = "#334155" # Lighter Slate (Slate 700)
    
    BORDER = "#334155"        # Slate 700
    BORDER_LIGHT = "#475569"  # Slate 600
    
    TEXT_MAIN = "#F8FAFC"     # Off-white (Slate 50)
    TEXT_MUTED = "#94A3B8"    # Muted Gray (Slate 400)
    TEXT_DIM = "#64748B"      # Darker Muted (Slate 500)
    
    # Status Colors
    SUCCESS = "#10B981"       # Emerald 500
    WARNING = "#F59E0B"       # Amber 500
    ERROR = "#EF4444"         # Red 500
    INFO = "#3B82F6"          # Blue 500
    ACCENT = "#8B5CF6"        # Violet 500 (For that "Pro" feel)
    
    # Status Colors
    STATUS_COLORS = {
        'MATCHED':   '#34D399',
        'MULTIPLE':  '#FBBF24',
        'NO_MATCH':  '#F87171',
        'UNCERTAIN': '#A78BFA',
        'PENDING':   '#64748B',
    }
    
    @staticmethod
    def get_main_stylesheet():
        return f"""
        QMainWindow {{
            background-color: {Theme.BACKGROUND};
        }}
        
        QWidget {{
            font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
            font-size: 13px;
            color: {Theme.TEXT_MAIN};
        }}
        
        /* Modern Scrollbars */
        QScrollBar:vertical {{
            border: none;
            background: {Theme.BACKGROUND};
            width: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {Theme.SURFACE_LIGHT};
            min-height: 20px;
            border-radius: 5px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {Theme.TEXT_DIM};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        /* Sidebar Styling */
        QFrame#Sidebar {{
            background-color: {Theme.SURFACE_DARK};
            border-right: 1px solid {Theme.BORDER};
        }}
        
        /* Navigation Buttons */
        QPushButton#NavButton {{
            background-color: transparent;
            color: {Theme.TEXT_MUTED};
            border: none;
            border-radius: 8px;
            padding: 10px 15px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
        }}
        
        QPushButton#NavButton:hover {{
            background-color: {Theme.SURFACE};
            color: {Theme.TEXT_MAIN};
        }}
        
        QPushButton#NavButton:checked {{
            background-color: {Theme.SURFACE_LIGHT};
            color: {Theme.PRIMARY};
        }}
        
        /* Action Buttons */
        QPushButton {{
            background-color: {Theme.PRIMARY};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 700;
        }}
        
        QPushButton:hover {{
            background-color: {Theme.PRIMARY_HOVER};
        }}
        
        QPushButton#SecondaryButton {{
            background-color: {Theme.SURFACE_LIGHT};
            color: {Theme.TEXT_MAIN};
            border: 1px solid {Theme.BORDER};
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 600;
        }}
        
        QPushButton#SecondaryButton:hover {{
            background-color: {Theme.PRIMARY};
            border-color: {Theme.PRIMARY};
            color: white;
        }}
        
        /* Input Fields */
        QLineEdit {{
            background-color: {Theme.SURFACE};
            border: 1px solid {Theme.BORDER};
            border-radius: 8px;
            padding: 8px 12px;
            color: {Theme.TEXT_MAIN};
            selection-background-color: {Theme.PRIMARY};
        }}
        
        QLineEdit:focus {{
            border: 1px solid {Theme.PRIMARY};
            background-color: {Theme.SURFACE_DARK};
        }}
        
        /* Tables */
        QTableWidget {{
            background-color: transparent;
            gridline-color: transparent;
            border: none;
            outline: none;
        }}
        
        QHeaderView, QHeaderView::section {{
            background-color: {Theme.SURFACE_DARK};
        }}
        
        QHeaderView::section {{
            background-color: {Theme.SURFACE_DARK};
            color: {Theme.TEXT_DIM};
            padding: 12px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            border: none;
            border-bottom: 1px solid {Theme.BORDER};
        }}
        
        QTableCornerButton::section {{
            background-color: {Theme.SURFACE_DARK};
            border: none;
            border-bottom: 1px solid {Theme.BORDER};
        }}
        
        QTableWidget {{
            background-color: transparent;
            border: none;
            gridline-color: transparent;
            selection-background-color: transparent;
            selection-color: white;
            outline: 0;
            show-decoration-selected: 1;
        }}
        
        QTableWidget::item {{
            border-bottom: 1px solid {Theme.SURFACE};
            padding: 15px;
            color: {Theme.TEXT_MAIN};
        }}
        
        QTableWidget::item:hover {{
            background-color: {Theme.SURFACE_LIGHT}40;
        }}
        
        QTableWidget::item:selected {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                            stop:0 {Theme.PRIMARY}, 
                                            stop:0.003 {Theme.PRIMARY}, 
                                            stop:0.004 {Theme.SURFACE_LIGHT}, 
                                            stop:1 {Theme.SURFACE_DARK});
            color: white;
            font-weight: 700;
        }}
        
        QTableWidget::item:selected:active {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                            stop:0 {Theme.PRIMARY}, 
                                            stop:0.003 {Theme.PRIMARY}, 
                                            stop:0.004 {Theme.SURFACE_LIGHT}, 
                                            stop:1 {Theme.SURFACE_DARK});
        }}

        /* Dialogs */
        QDialog {{
            background-color: {Theme.BACKGROUND};
        }}

        /* ComboBoxes */
        QComboBox {{
            background-color: {Theme.SURFACE};
            border: 1px solid {Theme.BORDER};
            border-radius: 6px;
            padding: 5px 10px;
            color: {Theme.TEXT_MAIN};
        }}
        QComboBox:hover {{
            border-color: {Theme.PRIMARY};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {Theme.SURFACE};
            border: 1px solid {Theme.BORDER};
            selection-background-color: {Theme.PRIMARY};
            color: {Theme.TEXT_MAIN};
            outline: none;
        }}

        /* SpinBoxes */
        QSpinBox {{
            background-color: {Theme.SURFACE};
            border: 1px solid {Theme.BORDER};
            border-radius: 6px;
            padding: 5px 10px;
            color: {Theme.TEXT_MAIN};
        }}
        QSpinBox:focus {{
            border-color: {Theme.PRIMARY};
        }}

        /* ListWidgets */
        QListWidget {{
            background-color: {Theme.SURFACE};
            border: 1px solid {Theme.BORDER};
            border-radius: 8px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 10px;
            border-radius: 6px;
            margin: 2px 5px;
        }}
        QListWidget::item:hover {{
            background-color: {Theme.SURFACE_LIGHT};
        }}
        QListWidget::item:selected {{
            background-color: {Theme.PRIMARY};
            color: white;
        }}

        /* CheckBoxes */
        QCheckBox {{
            spacing: 10px;
            color: {Theme.TEXT_MAIN};
            font-weight: 600;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 6px;
            border: 1px solid {Theme.BORDER};
            background-color: {Theme.SURFACE};
        }}
        QCheckBox::indicator:hover {{
            border-color: {Theme.PRIMARY};
        }}
        QCheckBox::indicator:checked {{
            background-color: {Theme.PRIMARY};
            border-color: {Theme.PRIMARY};
            image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
        }}
        """

    @staticmethod
    def create_hline():
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet(f"background-color: {Theme.BORDER}; max-height: 1px; border: none;")
        return line

    @staticmethod
    def get_table_style():
        return f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
            }}
            QHeaderView::section {{
                background-color: transparent;
                border: none;
                border-bottom: 2px solid {Theme.BORDER};
                padding: 12px;
                font-weight: 800;
                color: {Theme.TEXT_DIM};
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            QTableWidget::item {{
                padding: 4px 12px;
                border-bottom: 1px solid {Theme.SURFACE};
                color: {Theme.TEXT_MAIN};
            }}
            QTableWidget::item:selected {{
                background-color: {Theme.SURFACE};
                color: {Theme.PRIMARY};
                border-left: 3px solid {Theme.PRIMARY};
            }}
        """

    @staticmethod
    def get_action_button_style():
        return f"""
            QPushButton {{
                background-color: {Theme.SURFACE_LIGHT};
                color: {Theme.TEXT_MAIN};
                border: 1px solid {Theme.BORDER};
                border-radius: 5px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Theme.PRIMARY};
                border-color: {Theme.PRIMARY};
                color: white;
            }}
        """

    @staticmethod
    def get_primary_button_style():
        return f"""
            QPushButton {{
                background-color: {Theme.PRIMARY};
                color: white;
                border-radius: 8px;
                font-weight: 800;
                font-size: 13px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {Theme.PRIMARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {Theme.SURFACE_LIGHT};
                color: {Theme.TEXT_DIM};
            }}
        """

    @staticmethod
    def get_danger_button_style():
        return f"""
            QPushButton {{
                background-color: rgba(239, 68, 68, 0.1);
                color: #EF4444;
                border: 1px solid #EF4444;
                border-radius: 8px;
                font-weight: 800;
                font-size: 13px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: #EF4444;
                color: white;
            }}
        """

    @staticmethod
    def get_progress_bar_style():
        return f"""
            QProgressBar {{
                background-color: {Theme.BORDER};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.PRIMARY};
                border-radius: 2px;
            }}
        """

    @staticmethod
    def get_sidebar_list_style():
        return f"""
            QListWidget {{
                background: {Theme.SURFACE_DARK};
                border: none;
                border-right: 1px solid {Theme.BORDER};
                padding: 20px 10px;
            }}
            QListWidget::item {{
                padding: 12px 15px;
                color: {Theme.TEXT_MUTED};
                font-weight: 600;
                border-radius: 8px;
                margin-bottom: 2px;
            }}
            QListWidget::item:hover {{
                background: {Theme.SURFACE};
                color: {Theme.TEXT_MAIN};
            }}
            QListWidget::item:selected {{
                background: {Theme.SURFACE_LIGHT};
                color: {Theme.PRIMARY};
            }}
        """

    @staticmethod
    def get_scrollbar_style():
        return f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.BORDER};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Theme.TEXT_DIM};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """

    @staticmethod
    def get_sidebar_tree_style():
        return f"""
            QTreeWidget {{
                background: {Theme.SURFACE_DARK};
                border: none;
                border-right: 1px solid {Theme.BORDER};
                padding: 20px 5px;
                outline: none;
                show-decoration-selected: 0;
            }}
            QTreeWidget::item {{
                padding: 10px 12px;
                color: {Theme.TEXT_MUTED};
                font-weight: 600;
                border-radius: 8px;
                margin-top: 1px;
                margin-bottom: 1px;
            }}
            QTreeWidget::item:hover {{
                background: {Theme.SURFACE};
                color: {Theme.TEXT_MAIN};
            }}
            QTreeWidget::item:selected {{
                background: {Theme.SURFACE_LIGHT};
                color: {Theme.PRIMARY};
            }}
            QTreeWidget::branch {{
                background: transparent;
            }}
            QTreeWidget::branch:selected {{
                background: transparent;
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM5NGEzYjgiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iOSAxOCAxNSAxMiA5IDYiPjwvcG9seWxpbmU+PC9zdmc+);
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings  {{
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMzQjgyRjYiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iNiA5IDEyIDE1IDE4IDkiPjwvcG9seWxpbmU+PC9zdmc+);
            }}
        """
