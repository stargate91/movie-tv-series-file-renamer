from .palette import Palette

class InspectorStyles:
    @staticmethod
    def get_inspector_style():
        return f"""
            QFrame#Inspector {{
                background-color: {Palette.SURFACE_DARK};
                border-left: 1px solid {Palette.BORDER};
            }}
        """

    @staticmethod
    def get_inspector_title_style():
        return f"font-size: 18px; font-weight: 800; color: {Palette.TEXT_MAIN};"

    @staticmethod
    def get_inspector_year_style():
        return f"font-size: 15px; color: {Palette.PRIMARY}; font-weight: 700;"

    @staticmethod
    def get_inspector_overview_style():
        return f"color: {Palette.TEXT_MUTED}; line-height: 1.5; font-size: 12px;"

    @staticmethod
    def get_inspector_ep_frame_style():
        return f"background-color: {Palette.SURFACE}; border-radius: 10px; border: 1px solid {Palette.BORDER};"

    @staticmethod
    def get_inspector_ep_id_style():
        return f"font-size: 13px; color: {Palette.PRIMARY}; font-weight: 700; border: none;"

    @staticmethod
    def get_inspector_ep_title_style():
        return f"font-size: 14px; color: {Palette.TEXT_MAIN}; font-weight: 600; border: none;"

    @staticmethod
    def get_status_badge_style(color):
        return f"""
            QLabel {{
                color: {color}; background-color: {color}20;
                border: 1px solid {color}50; border-radius: 12px;
                font-weight: 800; font-size: 10px; padding: 2px 8px;
            }}
        """

    @staticmethod
    def get_inspector_section_header_style():
        return f"font-weight: 800; font-size: 10px; color: {Palette.TEXT_DIM}; letter-spacing: 1.5px;"

    @staticmethod
    def get_inspector_tech_frame_style():
        return f"background-color: {Palette.SURFACE}; border-radius: 10px; border: 1px solid {Palette.BORDER};"

    @staticmethod
    def get_inspector_tech_key_style():
        return f"color: {Palette.TEXT_DIM}; font-size: 9px; font-weight: 800; letter-spacing: 1px; border: none;"

    @staticmethod
    def get_inspector_tech_val_style():
        return f"color: {Palette.TEXT_MAIN}; font-size: 12px; font-weight: 600; border: none;"
