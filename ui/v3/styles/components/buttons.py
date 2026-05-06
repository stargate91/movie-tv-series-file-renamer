from ..palette import Palette

class ButtonStyles:
    @staticmethod
    def get_button_style(variant='primary', size='normal', radius=8):
        # Base styles based on variants
        styles = {
            'primary': {
                'bg': Palette.PRIMARY,
                'hover': Palette.PRIMARY_HOVER,
                'text': "white",
                'border': "none",
                'weight': '700'
            },
            'secondary': {
                'bg': Palette.SURFACE_LIGHT,
                'hover': Palette.SURFACE_LIGHTER,
                'text': Palette.TEXT_MAIN,
                'border': f"1px solid {Palette.BORDER}",
                'weight': '600'
            },
            'danger': {
                'bg': "rgba(220, 38, 38, 0.1)",
                'hover': Palette.ERROR,
                'text': Palette.ERROR,
                'border': f"1px solid {Palette.ERROR}",
                'weight': '800'
            },
            'ghost': {
                'bg': "transparent",
                'hover': Palette.SURFACE_LIGHT,
                'text': Palette.TEXT_MUTED,
                'border': "none",
                'weight': '600'
            },
            'action': {
                'bg': Palette.SURFACE_LIGHT,
                'hover': Palette.PRIMARY,
                'text': Palette.TEXT_MAIN,
                'border': f"1px solid {Palette.BORDER}",
                'weight': '600',
                'size': '11px',
                'padding': '2px 6px'
            }
        }
        
        v = styles.get(variant, styles['primary'])
        font_size = v.get('size', '13px' if size == 'normal' else '11px')
        padding = v.get('padding', '10px 20px')
        hover_text = "white" if variant in ['primary', 'danger', 'action'] else v['text']
        
        return f"""
            QPushButton {{
                background-color: {v['bg']};
                color: {v['text']};
                border: {v['border']};
                border-radius: {radius}px;
                padding: {padding};
                font-weight: {v['weight']};
                font-size: {font_size};
            }}
            QPushButton:hover {{
                background-color: {v['hover']};
                color: {hover_text};
                {f"border-color: {v['hover']};" if variant == 'secondary' else ""}
            }}
            QPushButton:disabled {{
                background-color: {Palette.SURFACE_LIGHT};
                color: {Palette.TEXT_DIM};
                border-color: {Palette.BORDER};
            }}
            QPushButton:checked {{
                background-color: {Palette.PRIMARY}20;
                color: {Palette.PRIMARY};
                border: 1px solid {Palette.PRIMARY};
            }}
        """

    @staticmethod
    def get_primary_button_style(): return ButtonStyles.get_button_style('primary')
    @staticmethod
    def get_secondary_button_style(): return ButtonStyles.get_button_style('secondary')
    @staticmethod
    def get_action_button_style(): return ButtonStyles.get_button_style('action', radius=5)
    @staticmethod
    def get_danger_button_style(): return ButtonStyles.get_button_style('danger')
    @staticmethod
    def get_save_button_style(): return ButtonStyles.get_button_style('primary', radius=12)
    @staticmethod
    def get_success_button_style():
        # Success is similar to primary but green
        s = ButtonStyles.get_button_style('primary', radius=12)
        return s.replace(Palette.PRIMARY, Palette.SUCCESS).replace(Palette.PRIMARY_HOVER, Palette.SUCCESS)

    @staticmethod
    def get_link_button_style():
        return f"color: {Palette.TEXT_MUTED}; font-size: 11px; text-decoration: underline; border: none; background: transparent; text-align: left;"

    @staticmethod
    def get_chip_style(variant='filter'):
        radius = 16 if variant == 'filter' else 12
        bg = Palette.SURFACE_LIGHT if variant == 'filter' else "transparent"
        padding = "0 16px" if variant == 'filter' else "4px 12px"
        
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {Palette.TEXT_MUTED};
                border: 1px solid {Palette.BORDER};
                border-radius: {radius}px;
                padding: {padding};
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Palette.SURFACE_LIGHTER};
                color: {Palette.TEXT_MAIN};
            }}
            QPushButton:checked {{
                background-color: {Palette.PRIMARY}20;
                color: {Palette.PRIMARY};
                border: 1px solid {Palette.PRIMARY};
            }}
        """

    @staticmethod
    def get_tag_chip_style(): return ButtonStyles.get_chip_style('filter')
    @staticmethod
    def get_filter_chip_style(): return ButtonStyles.get_chip_style('filter')
    @staticmethod
    def get_sub_chip_style(): return ButtonStyles.get_chip_style('sub')
    
    # Aliases for specialized buttons
    @staticmethod
    def get_abort_button_style(): return ButtonStyles.get_button_style('danger', radius=8)
    @staticmethod
    def get_settings_save_btn_style(): return ButtonStyles.get_button_style('primary', radius=8)
    @staticmethod
    def get_settings_cancel_btn_style(): return ButtonStyles.get_button_style('secondary', radius=8)

    @staticmethod
    def get_secondary_ghost_button_style(): return ButtonStyles.get_button_style('secondary', radius=8)

    @staticmethod
    def get_danger_ghost_button_style(): return ButtonStyles.get_button_style('danger', radius=6)

    @staticmethod
    def get_discovery_action_btn_style(variant=None):
        bg = "rgba(0, 0, 0, 0.05)"
        color = Palette.TEXT_MUTED
        border = Palette.BORDER
        
        if variant == 'danger':
            bg = "rgba(220, 38, 38, 0.1)"
            color = Palette.ERROR
            border = "rgba(220, 38, 38, 0.2)"
        elif variant == 'success':
            bg = "rgba(22, 163, 74, 0.1)"
            color = Palette.SUCCESS
            border = "rgba(22, 163, 74, 0.2)"
        elif variant == 'warning':
            bg = "rgba(202, 138, 4, 0.1)"
            color = Palette.WARNING
            border = "rgba(202, 138, 4, 0.2)"
        elif variant == 'primary':
            bg = "rgba(0, 120, 212, 0.1)"
            color = Palette.PRIMARY
            border = "rgba(0, 120, 212, 0.2)"
        elif variant == 'neutral':
            bg = "rgba(0, 0, 0, 0.05)"
            color = Palette.TEXT_MUTED
            border = "rgba(0, 0, 0, 0.1)"
        
        return f"""
            QPushButton {{
                background: {bg};
                color: {color};
                border-radius: 8px;
                font-size: 22px;
                font-weight: 700;
                border: 1px solid {border};
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {color};
                color: {Palette.SURFACE};
                border-color: {color};
            }}
            QPushButton:disabled {{
                background: transparent;
                color: {Palette.TEXT_DIM};
                border-color: {Palette.BORDER};
                opacity: 0.3;
            }}
        """

    @staticmethod
    def get_batch_button_style(variant='primary'):
        if variant == 'primary': 
            return ButtonStyles.get_primary_button_style()
        if variant == 'clear':
            return ButtonStyles.get_button_style('ghost', radius=8)
        # ignore, identify, restore etc. use secondary
        return ButtonStyles.get_button_style('secondary', radius=8)
