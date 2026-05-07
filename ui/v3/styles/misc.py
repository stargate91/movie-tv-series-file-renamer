from .palette import Palette
from .common import CommonStyles
from .components.buttons import ButtonStyles

class MiscStyles:
    # --- Typography Aliases ---
    @staticmethod
    def get_h1_style(): return CommonStyles.get_typography_style('h1', 'bold')
    
    @staticmethod
    def get_h2_style(): return CommonStyles.get_typography_style('h2', 'normal', Palette.TEXT_MUTED)
    
    @staticmethod
    def get_page_header_style(): return CommonStyles.get_typography_style('h2', 'black')
    
    @staticmethod
    def get_settings_title_style(): return CommonStyles.get_typography_style('h3', 'black')
    
    @staticmethod
    def get_setting_title_style(): return CommonStyles.get_typography_style('body', 'bold')
    
    @staticmethod
    def get_setting_desc_style(): return CommonStyles.get_typography_style('body', 'normal', Palette.TEXT_MUTED)
    
    @staticmethod
    def get_description_style(): return CommonStyles.get_typography_style('body', 'normal', Palette.TEXT_MUTED)
    
    @staticmethod
    def get_hint_style(): return f"font-style: italic; {CommonStyles.get_typography_style('small', 'normal', Palette.TEXT_DIM)}"
    
    @staticmethod
    def get_section_header_style(): return f"text-transform: uppercase; letter-spacing: 1.5px; {CommonStyles.get_typography_style('small', 'black', Palette.TEXT_DIM)}"

    # --- Container Aliases ---
    @staticmethod
    def get_card_style(): return CommonStyles.get_container_style('surface', 12)
    
    @staticmethod
    def get_settings_card_style(): return CommonStyles.get_container_style('surface', 12, padding=20)
    
    @staticmethod
    def get_danger_card_style(): return CommonStyles.get_container_style('danger', 12)
    
    @staticmethod
    def get_history_batch_card_style(): return f"margin-bottom: 15px; {CommonStyles.get_container_style('surface', 12)}"

    # --- Specialized Misc Styles ---
    @staticmethod
    def get_notification_bar_style():
        return f"""
            QWidget#NotifContainer {{
                background-color: {Palette.SURFACE_DARK}ee;
                border: 1px solid {Palette.PRIMARY};
                border-radius: 25px;
            }}
            QLabel {{
                {CommonStyles.get_typography_style('body', 'semibold')}
                border: none;
                background: transparent;
            }}
        """

    @staticmethod
    def get_notification_undo_style():
        return f"""
            QPushButton {{
                background-color: {Palette.PRIMARY};
                color: white;
                border-radius: 15px;
                font-weight: 800;
                font-size: 11px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background-color: {Palette.PRIMARY_HOVER}; }}
        """

    @staticmethod
    def get_notification_close_style():
        return f"color: {Palette.TEXT_MUTED}; border: none; font-size: 16px; background: transparent;"

    @staticmethod
    def get_drop_overlay_label_style():
        return f"background: transparent; border: none; {CommonStyles.get_typography_style('h2', 'black', 'white')}"

    @staticmethod
    def get_discovery_empty_label_style():
        return CommonStyles.get_typography_style('h3', 'normal', Palette.TEXT_DIM)

    @staticmethod
    def get_discovery_empty_hint_style():
        return CommonStyles.get_typography_style('body', 'normal', Palette.TEXT_MUTED)

    @staticmethod
    def get_history_batch_header_style():
        return f"background-color: {Palette.SURFACE_DARK}; border-bottom: 1px solid {Palette.BORDER}; border-top-left-radius: 12px; border-top-right-radius: 12px;"

    @staticmethod
    def get_history_timestamp_style():
        return CommonStyles.get_typography_style('small', 'semibold', Palette.TEXT_DIM)

    @staticmethod
    def get_history_count_style():
        return CommonStyles.get_typography_style('body', 'black', Palette.PRIMARY)

    @staticmethod
    def get_history_row_style():
        return f"border-bottom: 1px solid {Palette.BORDER}33;"

    @staticmethod
    def get_history_old_name_style():
        return f"font-family: monospace; {CommonStyles.get_typography_style('small', 'normal', Palette.TEXT_DIM)}"

    @staticmethod
    def get_history_new_name_style():
        return f"font-family: monospace; {CommonStyles.get_typography_style('body', 'bold', Palette.SUCCESS)}"

    @staticmethod
    def get_history_expand_button_style():
        return f"color: {Palette.TEXT_DIM}; background: transparent; border: none; font-weight: 700;"

    @staticmethod
    def get_monospace_label_style():
        return f"font-family: 'Consolas', 'Monaco', monospace; {CommonStyles.get_typography_style('small', 'normal', Palette.TEXT_DIM)}"

    @staticmethod
    def get_preview_summary_style():
        return CommonStyles.get_typography_style('body', 'normal', Palette.TEXT_DIM)

    @staticmethod
    def get_preview_title_style():
        return CommonStyles.get_typography_style('h4', 'black')

    @staticmethod
    def get_preview_panel_style():
        return f"background-color: {Palette.SURFACE}; border-left: 1px solid {Palette.BORDER};"

    @staticmethod
    def get_preview_meta_style():
        return f"margin-bottom: 10px; {CommonStyles.get_typography_style('small', 'semibold', Palette.TEXT_MUTED)}"

    @staticmethod
    def get_preview_overview_style():
        return f"line-height: 1.4; {CommonStyles.get_typography_style('body', 'normal', Palette.TEXT_DIM)}"

    @staticmethod
    def get_batch_bar_style():
        return f"background-color: {Palette.SURFACE_DARK}; border-top: 2px solid {Palette.PRIMARY}; padding: 10px;"

    @staticmethod
    def get_batch_label_style():
        return CommonStyles.get_typography_style('h4', 'bold')

    @staticmethod
    def get_drop_overlay_style():
        return f"background-color: {Palette.PRIMARY}CC; border: 4px dashed white; border-radius: 20px;"

    @staticmethod
    def get_card_header_style():
        return f"margin-bottom: 5px; {CommonStyles.get_typography_style('body', 'bold')}"

    @staticmethod
    def get_card_title_style(): return CommonStyles.get_typography_style('h3', 'black')

    @staticmethod
    def get_card_description_style(): return CommonStyles.get_typography_style('body', 'normal', Palette.TEXT_MUTED)

    @staticmethod
    def get_danger_title_style():
        return CommonStyles.get_typography_style('h4', 'bold', Palette.ERROR)

    @staticmethod
    def get_history_undo_button_style():
        return ButtonStyles.get_button_style('secondary', radius=6)

    @staticmethod
    def get_scroll_area_style():
        return "background: transparent; border: none;"

    @staticmethod
    def get_scroll_area_transparent_style():
        return MiscStyles.get_scroll_area_style()

    @staticmethod
    def get_inner_tab_widget_style():
        return f"""
            QTabWidget::pane {{ border: 1px solid {Palette.BORDER}; border-radius: 8px; background: {Palette.SURFACE}; }}
            QTabBar::tab {{ 
                background: {Palette.SURFACE_DARK}; 
                color: {Palette.TEXT_MUTED}; 
                padding: 8px 15px; 
                border: 1px solid {Palette.BORDER}; 
                border-bottom: none; 
                border-radius: 6px 6px 0 0; 
                margin-right: 2px;
                font-weight: 600;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{ 
                background: {Palette.SURFACE}; 
                color: {Palette.PRIMARY}; 
                border-bottom: 2px solid {Palette.PRIMARY}; 
            }}
            QTabBar::tab:hover:!selected {{
                background: {Palette.SURFACE_LIGHT};
            }}
        """

    @staticmethod
    def get_master_toggle_style():
        """Bold primary-colored checkbox used as a section master toggle."""
        return f"QCheckBox {{ font-weight: 700; font-size: 15px; color: {Palette.PRIMARY}; }}"

    @staticmethod
    def get_info_box_style():
        """Bordered card-like box for grouped info (e.g., extension lists)."""
        return f"""
            QFrame {{
                background-color: {Palette.SURFACE_LIGHT};
                border: 1px solid {Palette.BORDER};
                border-radius: 8px;
                padding: 15px;
            }}
        """

    @staticmethod
    def get_stat_value_style():
        """Large bold number for dashboard stat cards."""
        return f"font-size: 36px; font-weight: 800; color: {Palette.PRIMARY};"
