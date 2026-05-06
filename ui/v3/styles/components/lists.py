from ..palette import Palette

class ListStyles:
    @staticmethod
    def get_sidebar_list_style():
        return ListStyles.get_list_widget_style()

    @staticmethod
    def get_list_widget_style():
        return f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 8px;
                color: {Palette.TEXT_MAIN};
            }}
            QListWidget::item:selected {{
                background-color: {Palette.PRIMARY}20;
                color: {Palette.PRIMARY};
                font-weight: bold;
            }}
            QListWidget::item:hover {{
                background-color: {Palette.SURFACE_LIGHT};
            }}
        """

    @staticmethod
    def get_settings_nav_list_style():
        return f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
                padding: 10px;
            }}
            QListWidget::item {{
                padding: 12px 16px;
                border-radius: 8px;
                color: {Palette.TEXT_MUTED};
                margin-bottom: 4px;
                font-weight: 600;
            }}
            QListWidget::item:selected {{
                background-color: {Palette.PRIMARY};
                color: white;
            }}
            QListWidget::item:hover:!selected {{
                background-color: {Palette.SURFACE_LIGHT};
                color: {Palette.TEXT_MAIN};
            }}
        """

    @staticmethod
    def get_context_menu_style():
        return f"""
            QMenu {{
                background-color: {Palette.SURFACE};
                border: 1px solid {Palette.BORDER};
                border-radius: 8px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 25px;
                border-radius: 4px;
                color: {Palette.TEXT_MAIN};
                font-size: 13px;
            }}
            QMenu::item:selected {{
                background-color: {Palette.PRIMARY};
                color: white;
            }}
            QMenu::separator {{
                height: 1px;
                background: {Palette.BORDER};
                margin: 4px 10px;
            }}
        """
