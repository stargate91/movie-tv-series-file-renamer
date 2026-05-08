from ..palette import Palette
from ..icons import IconManager

class InputStyles:
    @staticmethod
    def get_input_style(variant='default'):
        bg = Palette.SURFACE if variant == 'default' else Palette.SURFACE_DARK
        padding = "8px 12px" if variant == 'default' else "0 10px"
        radius = 8 if variant == 'default' else 6
        
        return f"""
            QLineEdit {{
                background-color: {bg};
                color: {Palette.TEXT_MAIN};
                border: 1px solid {Palette.BORDER};
                border-radius: {radius}px;
                padding: {padding};
                font-size: 13px;
                selection-background-color: {Palette.PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {Palette.PRIMARY};
                background-color: {Palette.SURFACE if variant != 'default' else Palette.SURFACE_LIGHT};
            }}
            QLineEdit:disabled {{
                background: {Palette.SURFACE_DARK};
                color: {Palette.TEXT_DIM};
                border-color: {Palette.SURFACE_LIGHT};
            }}
        """

    @staticmethod
    def get_settings_input_style():
        return InputStyles.get_input_style('settings')

    @staticmethod
    def get_input_label_style():
        return f"font-weight: 600; font-size: 13px; color: {Palette.TEXT_MAIN}; background: transparent; border: none;"

    @staticmethod
    def get_spinbox_style():
        return f"""
            QSpinBox {{
                background: {Palette.SURFACE_DARK};
                border: 1px solid {Palette.BORDER};
                border-radius: 6px;
                padding: 5px;
                color: {Palette.TEXT_MAIN};
            }}
            QSpinBox:focus {{ border-color: {Palette.PRIMARY}; }}
        """

    @staticmethod
    def get_combobox_style():
        return f"""
            QComboBox {{
                background-color: {Palette.SURFACE_DARK};
                border: 1px solid {Palette.BORDER};
                border-radius: 6px;
                padding: 5px 10px;
                color: {Palette.TEXT_MAIN};
                font-size: 13px;
                min-height: 20px;
            }}
            QComboBox:hover {{
                border-color: {Palette.PRIMARY};
                background-color: {Palette.SURFACE_LIGHT};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: url("{IconManager.get_icon_path("chevron-down", 14, Palette.TEXT_DIM)}");
                width: 14px;
                height: 14px;
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Palette.BACKGROUND};
                border: 1px solid {Palette.BORDER};
                selection-background-color: {Palette.PRIMARY};
                selection-color: white;
                outline: none;
            }}
        """
    @staticmethod
    def get_accent_combobox_style():
        return f"""
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
                width: 34px;
                border-left: 1px solid {Palette.BORDER};
                background-color: {Palette.SURFACE_DARK};
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {Palette.PRIMARY};
                width: 0;
                height: 0;
                margin-top: 2px;
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
        """
