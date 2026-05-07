from PySide6.QtWidgets import QFrame
from .palette import Palette

class CommonStyles:
    @staticmethod
    def get_main_stylesheet():
        return f"""
        QMainWindow {{
            background-color: {Palette.BACKGROUND};
        }}
        
        QWidget {{
            font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
            font-size: 13px;
            color: {Palette.TEXT_MAIN};
        }}
        
        /* Modern Scrollbars */
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {Palette.SURFACE_LIGHT};
            min-height: 20px;
            border-radius: 5px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {Palette.SURFACE_LIGHTER};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        /* Sidebar Styling */
        QFrame#Sidebar {{
            background-color: {Palette.SURFACE_DARK};
            border-right: 1px solid {Palette.BORDER};
        }}
        
        /* Navigation Buttons */
        QPushButton#NavButton {{
            background-color: transparent;
            color: {Palette.TEXT_MUTED};
            border: none;
            border-radius: 8px;
            padding: 10px 15px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
        }}
        
        QPushButton#NavButton:hover {{
            background-color: {Palette.SURFACE};
            color: {Palette.TEXT_MAIN};
        }}
        
        QPushButton#NavButton:checked {{
            background-color: {Palette.SURFACE_LIGHT};
            color: {Palette.PRIMARY};
        }}
        
        /* Action Buttons */
        QPushButton {{
            background-color: {Palette.PRIMARY};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 700;
        }}
        
        QPushButton:hover {{
            background-color: {Palette.PRIMARY_HOVER};
        }}
        
        QPushButton#SecondaryButton {{
            background-color: {Palette.SURFACE_LIGHT};
            color: {Palette.TEXT_MAIN};
            border: 1px solid {Palette.BORDER};
            padding: 10px 15px;
            text-align: left;
            font-size: 13px;
            font-weight: 600;
            border-radius: 8px;
        }}
        
        QPushButton#SecondaryButton:hover {{
            background-color: {Palette.SURFACE_LIGHTER};
            border-color: {Palette.PRIMARY};
            color: {Palette.TEXT_MAIN};
        }}
        
        /* Input Fields */
        QLineEdit {{
            background-color: {Palette.SURFACE};
            border: 1px solid {Palette.BORDER};
            border-radius: 8px;
            padding: 8px 12px;
            color: {Palette.TEXT_MAIN};
            selection-background-color: {Palette.PRIMARY};
        }}
        
        QLineEdit:focus {{
            border: 1px solid {Palette.PRIMARY};
            background-color: {Palette.SURFACE_DARK};
        }}
        
        /* Tables */
        QTableWidget {{
            background-color: transparent;
            gridline-color: transparent;
            border: none;
            outline: none;
        }}
        
        QHeaderView, QHeaderView::section {{
            background-color: {Palette.SURFACE_DARK};
        }}
        
        QHeaderView::section {{
            background-color: {Palette.SURFACE_DARK};
            color: {Palette.TEXT_DIM};
            padding: 12px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            border: none;
            border-bottom: 1px solid {Palette.BORDER};
        }}
        
        QTableCornerButton::section {{
            background-color: {Palette.SURFACE_DARK};
            border: none;
            border-bottom: 1px solid {Palette.BORDER};
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
            border-bottom: 1px solid {Palette.SURFACE};
            padding: 15px;
            color: {Palette.TEXT_MAIN};
        }}
        
        QTableWidget::item:hover {{
            background-color: {Palette.SURFACE_LIGHT}40;
        }}
        
        QTableWidget::item:selected {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                            stop:0 {Palette.PRIMARY}, 
                                            stop:0.003 {Palette.PRIMARY}, 
                                            stop:0.004 {Palette.SURFACE_LIGHT}, 
                                            stop:1 {Palette.SURFACE_DARK});
            color: white;
            font-weight: 700;
        }}
        
        QTableWidget::item:selected:active {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                            stop:0 {Palette.PRIMARY}, 
                                            stop:0.003 {Palette.PRIMARY}, 
                                            stop:0.004 {Palette.SURFACE_LIGHT}, 
                                            stop:1 {Palette.SURFACE_DARK});
        }}

        /* Dialogs */
        QDialog {{
            background-color: {Palette.BACKGROUND};
        }}

        /* ComboBoxes */
        QComboBox {{
            background-color: {Palette.SURFACE};
            border: 1px solid {Palette.BORDER};
            border-radius: 8px;
            padding: 8px 35px 8px 12px;
            color: {Palette.TEXT_MAIN};
        }}
        QComboBox:hover {{
            border-color: {Palette.PRIMARY};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border-left: 1px solid {Palette.BORDER};
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
        }}
        QComboBox::down-arrow {{
            image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM5NGEzYjgiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iNiA5IDEyIDE1IDE4IDkiPjwvcG9seWxpbmU+PC9zdmc+);
            width: 16px;
            height: 16px;
        }}
        QComboBox QLineEdit {{
            background: transparent;
            border: none;
            color: {Palette.TEXT_MAIN};
            padding: 0;
            margin: 0;
        }}
        QComboBox QAbstractItemView {{
            background-color: {Palette.SURFACE} !important;
            border: 1px solid {Palette.BORDER};
            selection-background-color: {Palette.PRIMARY};
            selection-color: white;
            color: {Palette.TEXT_MAIN};
            padding: 4px;
            outline: none;
        }}
        QComboBox QListView {{
            background-color: {Palette.SURFACE} !important;
            color: {Palette.TEXT_MAIN};
            selection-background-color: {Palette.PRIMARY};
            selection-color: white;
        }}
        QComboBox::item {{
            padding: 8px 12px;
            color: {Palette.TEXT_MAIN};
            background-color: transparent;
        }}
        QComboBox::item:selected {{
            background-color: {Palette.PRIMARY} !important;
            color: white !important;
        }}

        /* SpinBoxes */
        QSpinBox {{
            background-color: {Palette.SURFACE};
            border: 1px solid {Palette.BORDER};
            border-radius: 6px;
            padding: 5px 10px;
            color: {Palette.TEXT_MAIN};
        }}
        QSpinBox:focus {{
            border-color: {Palette.PRIMARY};
        }}

        /* ListWidgets */
        QListWidget {{
            background-color: {Palette.SURFACE};
            border: 1px solid {Palette.BORDER};
            border-radius: 8px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 10px;
            border-radius: 6px;
            margin: 2px 5px;
        }}
        QListWidget::item:hover {{
            background-color: {Palette.SURFACE_LIGHT};
        }}
        QListWidget::item:selected {{
            background-color: {Palette.PRIMARY};
            color: white;
        }}

        /* CheckBoxes */
        QCheckBox {{
            spacing: 10px;
            color: {Palette.TEXT_MAIN};
            font-weight: 600;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 6px;
            border: 1px solid {Palette.BORDER};
            background-color: {Palette.SURFACE};
        }}
        QCheckBox::indicator:hover {{
            border-color: {Palette.PRIMARY};
        }}
        QCheckBox::indicator:checked {{
            background-color: {Palette.PRIMARY};
            border-color: {Palette.PRIMARY};
            image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
        }}

        /* Context Menus */
        QMenu {{
            background-color: {Palette.SURFACE};
            border: 1px solid {Palette.BORDER};
            padding: 0px;
            margin: 0px;
        }}
        QMenu::item {{
            background-color: {Palette.SURFACE};
            padding: 8px 30px 8px 25px;
            color: {Palette.TEXT_MAIN};
            margin: 0px;
        }}
        QMenu::item:selected {{
            background-color: {Palette.SURFACE_DARK};
            color: {Palette.TEXT_MAIN};
        }}
        QMenu::icon {{
            background-color: transparent;
            padding-left: 10px;
        }}
        QMenu::separator {{
            height: 1px;
            background: {Palette.BORDER};
            margin: 0px;
        }}
        """

    @staticmethod
    def get_typography_style(level='body', weight='normal', color=None):
        sizes = {
            'h1': '32px', 'h2': '24px', 'h3': '20px', 'h4': '18px',
            'body': '13px', 'small': '11px', 'tiny': '10px'
        }
        weights = {
            'normal': '400', 'semibold': '600', 'bold': '700', 'black': '800'
        }
        
        c = color or Palette.TEXT_MAIN
        size = sizes.get(level, '13px')
        w = weights.get(weight, '400')
        
        return f"font-size: {size}; font-weight: {w}; color: {c};"

    @staticmethod
    def get_container_style(variant='surface', radius=12, padding=0):
        bgs = {
            'surface': Palette.SURFACE,
            'dark': Palette.SURFACE_DARK,
            'background': Palette.BACKGROUND,
            'danger': "rgba(239, 68, 68, 0.05)"
        }
        bg = bgs.get(variant, Palette.SURFACE)
        border_color = Palette.BORDER if variant != 'danger' else "rgba(239, 68, 68, 0.2)"
        
        p_style = f"padding: {padding}px;" if padding > 0 else ""
        return f"background-color: {bg}; border: 1px solid {border_color}; border-radius: {radius}px; {p_style}"

    @staticmethod
    def create_hline():
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet(f"background-color: {Palette.BORDER}; max-height: 1px; border: none;")
        return line

    @staticmethod
    def get_scrollbar_style():
        return f"""
            QScrollBar:vertical {{
                border: none;
                background: {Palette.BACKGROUND};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {Palette.SURFACE_LIGHT};
                min-height: 20px;
                border-radius: 5px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Palette.TEXT_DIM};
            }}
        """

    @staticmethod
    def get_scroll_area_style():
        return "background: transparent; border: none;"
