class Palette:
    # Core Colors (Windows Light Inspired)
    BACKGROUND = "#FFFFFF"    
    SURFACE = "#FFFFFF"       
    SURFACE_DARK = "#F3F4F6"  
    SURFACE_LIGHT = "#E5E7EB" 
    SURFACE_LIGHTER = "#D1D5DB"
    
    PRIMARY = "#0078D4"       
    PRIMARY_HOVER = "#005A9E" 
    
    BORDER = "#E5E7EB"        
    BORDER_LIGHT = "#F3F4F6"
    
    TEXT_MAIN = "#111827"     
    TEXT_MUTED = "#4B5563"    
    TEXT_DIM = "#9CA3AF"      
    
    # Status Colors (Strong/Solid for Badges)
    STATUS_COLORS = {
        'PENDING':   '#605E5C', # Neutral Gray
        'MATCHED':   '#107C10', # Strong Windows Green
        'MULTIPLE':  '#D83B01', # Strong Windows Orange
        'NO_MATCH':  '#A4262C', # Strong Windows Red
        'UNCERTAIN': '#7C3AED', # Strong Purple (Violet 600)
        'LINKED':    '#0078D4', # Windows Blue
        'ORPHANED':  '#CA8A04', # Dark Amber
        'CONFLICT':  '#A4262C', # Red
        'IGNORED':   '#8A8886', # Medium Gray
    }
    
    # Semantic Aliases
    SUCCESS = STATUS_COLORS['MATCHED']
    WARNING = STATUS_COLORS['MULTIPLE']
    ERROR = STATUS_COLORS['NO_MATCH']
    INFO = STATUS_COLORS['LINKED']
