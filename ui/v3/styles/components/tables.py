from ..palette import Palette
from ..common import CommonStyles

class TableStyles:
    @staticmethod
    def get_table_base_style():
        return f"""
            QTableWidget {{
                background-color: transparent;
                gridline-color: transparent;
                selection-background-color: transparent;
                outline: 0;
                border: none;
            }}
            QHeaderView::section {{
                background-color: transparent;
                border: none;
                border-bottom: 2px solid {Palette.BORDER};
                padding: 12px;
                {CommonStyles.get_typography_style('tiny', 'black', Palette.TEXT_DIM)}
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
        """

    @staticmethod
    def get_table_style():
        return f"""
            {TableStyles.get_table_base_style()}
            QTableWidget::item {{
                padding: 4px 12px;
                border-bottom: 1px solid {Palette.SURFACE_DARK};
                color: {Palette.TEXT_MAIN};
            }}
            QTableWidget::item:selected {{
                background-color: {Palette.SURFACE_DARK};
                color: {Palette.PRIMARY};
                border-left: 3px solid {Palette.PRIMARY};
            }}
        """

    @staticmethod
    def get_discovery_table_style():
        return f"""
            {TableStyles.get_table_base_style()}
            QTableWidget::item {{
                border-bottom: 1px solid {Palette.SURFACE_DARK};
                padding: 12px;
                color: {Palette.TEXT_MAIN};
            }}
            QTableWidget::item:selected {{
                color: {Palette.PRIMARY};
                font-weight: 700;
            }}
        """

    @staticmethod
    def get_status_label_style(color=None):
        if not color:
            return CommonStyles.get_typography_style('small', 'semibold', Palette.TEXT_DIM)
        return f"""
            QLabel {{
                color: white !important; 
                background-color: {color}; 
                border-radius: 4px; 
                padding: 2px 8px; 
                font-weight: 800;
                font-size: 10px;
                text-transform: uppercase;
                border: none;
            }}
        """

    @staticmethod
    def get_batch_card_style():
        return f"margin: 5px 0; {CommonStyles.get_container_style('surface', 12)}"
