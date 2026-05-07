from ..palette import Palette

class ProgressStyles:
    @staticmethod
    def get_progress_bar_style():
        return f"""
            QProgressBar {{
                background-color: {Palette.PROGRESS_BG};
                border: none;
                border-radius: 2px;
                height: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {Palette.PROGRESS_CHUNK};
                border-radius: 2px;
            }}
        """

    @staticmethod
    def get_progress_bar_detailed_style():
        return f"""
            QProgressBar {{ 
                background: {Palette.PROGRESS_BG}; 
                border: 1px solid {Palette.BORDER}; 
                border-radius: 7px; 
                text-align: center;
                color: {Palette.TEXT_MAIN if Palette.PROGRESS_BG == Palette.BACKGROUND else 'white'};
                font-weight: 800;
                font-size: 10px;
                height: 14px;
            }} 
            QProgressBar::chunk {{ 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Palette.PROGRESS_CHUNK}, stop:1 {Palette.ACCENT});
                border-radius: 6px; 
            }}
        """
