from .palette import Palette

class NavigationStyles:
    @staticmethod
    def get_sidebar_title_style():
        return f"font-size: 24px; font-weight: 900; color: {Palette.PRIMARY}; letter-spacing: -0.5px;"

    @staticmethod
    def get_sidebar_subtitle_style():
        return f"font-size: 11px; font-weight: 700; color: {Palette.TEXT_DIM}; text-transform: uppercase; letter-spacing: 2px;"

    @staticmethod
    def get_tab_widget_style():
        return f"""
            QTabWidget::pane {{ border: 1px solid {Palette.BORDER}; border-radius: 12px; background: {Palette.SURFACE_DARK}; }}
            QTabBar::tab {{ background: {Palette.SURFACE}; color: {Palette.TEXT_MUTED}; padding: 12px 24px; border: 1px solid {Palette.BORDER}; border-bottom: none; border-radius: 8px 8px 0 0; font-weight: 700; font-size: 13px; margin-right: 4px; }}
            QTabBar::tab:selected {{ background: {Palette.SURFACE_DARK}; color: {Palette.PRIMARY}; border-bottom: 2px solid {Palette.PRIMARY}; }}
            QTabBar::tab:hover {{ background: {Palette.SURFACE_LIGHT}; color: {Palette.TEXT_MAIN}; }}
        """

    @staticmethod
    def get_inner_tab_widget_style():
        return f"""
            QTabWidget::pane {{ border: 1px solid {Palette.BORDER}; border-radius: 8px; background: {Palette.SURFACE_DARK}; }}
            QTabBar::tab {{ background: {Palette.SURFACE}; color: {Palette.TEXT_MUTED}; padding: 12px 24px; border: 1px solid {Palette.BORDER}; border-bottom: none; border-radius: 8px 8px 0 0; font-weight: 700; font-size: 13px; margin-right: 4px; }}
            QTabBar::tab:selected {{ background: {Palette.SURFACE_DARK}; color: {Palette.PRIMARY}; border-bottom: 2px solid {Palette.PRIMARY}; }}
            QTabBar::tab:hover {{ background: {Palette.SURFACE_LIGHT}; color: {Palette.TEXT_MAIN}; }}
        """

    @staticmethod
    def get_settings_sidebar_style():
        return f"background: {Palette.SURFACE_DARK}; border-right: 1px solid {Palette.BORDER};"

    @staticmethod
    def get_settings_content_style():
        return "background: transparent; border: none;"

    @staticmethod
    def get_support_button_style():
        return f"""
            QPushButton {{
                background: {Palette.SURFACE_LIGHT};
                color: {Palette.TEXT_MAIN};
                border: 1px solid {Palette.BORDER};
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                padding: 10px 15px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {Palette.SURFACE_LIGHTER};
                border-color: {Palette.TEXT_DIM};
            }}
        """
