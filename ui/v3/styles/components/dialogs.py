from ..palette import Palette
from ..common import CommonStyles

class DialogStyles:
    @staticmethod
    def get_data_sheet_style():
        return f"""
            QDialog {{ background: {Palette.BACKGROUND}; }}
            QTabWidget::pane {{ border: 1px solid {Palette.BORDER}; border-radius: 8px; background: {Palette.SURFACE_DARK}; }}
            QTabBar::tab {{ background: {Palette.SURFACE}; color: {Palette.TEXT_MUTED}; padding: 10px 20px; border: 1px solid {Palette.BORDER}; border-bottom: none; border-radius: 6px 6px 0 0; font-weight: 600; }}
            QTabBar::tab:selected {{ background: {Palette.SURFACE_DARK}; color: {Palette.TEXT_MAIN}; border-bottom: 2px solid {Palette.PRIMARY}; }}
            QTextEdit {{ background: {Palette.SURFACE}; color: {Palette.TEXT_MAIN}; border: 1px solid {Palette.BORDER}; border-radius: 6px; font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px; padding: 8px; }}
            QTreeWidget {{ background: {Palette.SURFACE}; color: {Palette.TEXT_MAIN}; border: 1px solid {Palette.BORDER}; border-radius: 6px; }}
            QTreeWidget::item {{ padding: 6px 0; }}
            QHeaderView::section {{ background: {Palette.SURFACE_LIGHT}; color: {Palette.TEXT_MUTED}; font-weight: 700; border: none; padding: 8px; }}
        """

    @staticmethod
    def get_preview_dialog_style():
        return f"background-color: {Palette.BACKGROUND}; color: {Palette.TEXT_MAIN};"

    @staticmethod
    def get_preview_header_style():
        return CommonStyles.get_typography_style('h3', 'black')

    @staticmethod
    def get_preview_search_input_style():
        return f"""
            QLineEdit {{
                background: {Palette.SURFACE_DARK};
                border: 1px solid {Palette.BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                color: {Palette.TEXT_MAIN};
            }}
            QLineEdit:focus {{ border-color: {Palette.PRIMARY}; }}
        """

    @staticmethod
    def get_preview_list_header_style():
        return f"background: {Palette.SURFACE_DARK}; border-bottom: 2px solid {Palette.BORDER};"

    @staticmethod
    def get_preview_col_label_style():
        return f"letter-spacing: 1px; {CommonStyles.get_typography_style('tiny', 'black', Palette.TEXT_DIM)}"

    @staticmethod
    def get_preview_row_style(is_collision=False):
        bg_color = "rgba(220, 38, 38, 0.05)" if is_collision else Palette.SURFACE
        border_color = Palette.ERROR if is_collision else Palette.BORDER
        hover_bg = Palette.SURFACE_LIGHT if not is_collision else "rgba(220, 38, 38, 0.1)"
        
        return f"""
            QFrame#Row {{ 
                background-color: {bg_color}; 
                border-bottom: 1px solid {border_color};
            }}
            QFrame#Row:hover {{ background-color: {hover_bg}; }}
        """

    @staticmethod
    def get_preview_old_name_style():
        return f"font-family: monospace; {CommonStyles.get_typography_style('small', 'normal', Palette.TEXT_DIM)}"

    @staticmethod
    def get_preview_arrow_style():
        return f"color: {Palette.PRIMARY}; font-weight: 900; font-size: 16px;"

    @staticmethod
    def get_preview_new_name_style(color):
        return f"color: {color}; font-family: monospace; {CommonStyles.get_typography_style('body', 'bold')}"

    @staticmethod
    def get_preview_remove_btn_style():
        return f"""
            QPushButton {{ background: transparent; color: {Palette.ERROR}; font-size: 16px; border-radius: 4px; }}
            QPushButton:hover {{ background: rgba(220, 38, 38, 0.1); }}
        """

    @staticmethod
    def get_preview_cancel_btn_style():
        from .buttons import ButtonStyles
        return ButtonStyles.get_button_style('secondary')

    @staticmethod
    def get_tree_style():
        return f"QTreeWidget {{ alternate-background-color: {Palette.SURFACE_DARK}; }}"
