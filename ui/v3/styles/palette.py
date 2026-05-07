class Palette:
    # Current active values (default to light)
    BACKGROUND = "#FFFFFF"    
    SURFACE = "#FFFFFF"       
    SURFACE_DARK = "#F3F4F6"  
    SURFACE_LIGHT = "#E5E7EB" 
    SURFACE_LIGHTER = "#D1D5DB"
    
    PRIMARY = "#0078D4"       
    PRIMARY_HOVER = "#005A9E" 
    ACCENT = "#00BCF2"
    
    BORDER = "#E5E7EB"        
    BORDER_LIGHT = "#F3F4F6"
    
    TEXT_MAIN = "#111827"     
    TEXT_MUTED = "#4B5563"    
    TEXT_DIM = "#9CA3AF"

    # Progress Bar Specific (Ensures visibility in both modes)
    PROGRESS_BG = "#E5E7EB"
    PROGRESS_CHUNK = "#0078D4"
    
    # Semantic Aliases
    SUCCESS = "#107C10"
    WARNING = "#D83B01"
    ERROR = "#A4262C"
    INFO = "#0078D4"
    
    STATUS_COLORS = {
        'PENDING':   '#605E5C',
        'MATCHED':   '#107C10',
        'MULTIPLE':  '#D83B01',
        'NO_MATCH':  '#A4262C',
        'UNCERTAIN': '#D97706', 
        'LINKED':    '#0078D4',
        'ORPHANED':  '#CA8A04',
        'CONFLICT':  '#A4262C',
        'IGNORED':   '#8A8886',
    }

    @classmethod
    def apply_theme(cls, mode="light"):
        """Dynamically updates class attributes based on theme mode."""
        # We update both Palette and whatever subclass was used to call this (e.g. Theme)
        targets = [Palette]
        if cls != Palette:
            targets.append(cls)
        
        for target in targets:
            if mode == "dark":
                target.BACKGROUND = "#0F172A"    # Deep Navy/Gray
                target.SURFACE = "#1E293B"       # Slate 800
                target.SURFACE_DARK = "#0F172A"  # Slate 900
                target.SURFACE_LIGHT = "#334155" # Slate 700
                target.SURFACE_LIGHTER = "#475569" # Slate 600
                
                target.PRIMARY = "#3B82F6"       # Blue 500
                target.PRIMARY_HOVER = "#60A5FA" # Blue 400
                target.ACCENT = "#818CF8"        # Indigo 400
                
                target.BORDER = "#334155"        # Slate 700
                target.BORDER_LIGHT = "#1E293B"  # Slate 800
                
                target.TEXT_MAIN = "#F8FAFC"     # Slate 50
                target.TEXT_MUTED = "#94A3B8"    # Slate 400
                target.TEXT_DIM = "#64748B"      # Slate 500

                # Dark Mode Progress Colors (More contrast against Surface)
                target.PROGRESS_BG = "#334155"   # Slate 700
                target.PROGRESS_CHUNK = "#3B82F6"
                
                target.STATUS_COLORS.update({
                    'PENDING':   '#94A3B8',
                    'MATCHED':   '#22C55E', 
                    'MULTIPLE':  '#F97316', 
                    'NO_MATCH':  '#EF4444', 
                    'UNCERTAIN': '#F59E0B', 
                    'IGNORED':   '#64748B',
                })
            else:
                target.BACKGROUND = "#FFFFFF"    
                target.SURFACE = "#FFFFFF"       
                target.SURFACE_DARK = "#F3F4F6"  
                target.SURFACE_LIGHT = "#E5E7EB" 
                target.SURFACE_LIGHTER = "#D1D5DB"
                
                target.PRIMARY = "#0078D4"       
                target.PRIMARY_HOVER = "#005A9E" 
                target.ACCENT = "#00BCF2"
                
                target.BORDER = "#E5E7EB"        
                target.BORDER_LIGHT = "#F3F4F6"
                
                target.TEXT_MAIN = "#111827"     
                target.TEXT_MUTED = "#4B5563"    
                target.TEXT_DIM = "#9CA3AF"

                target.PROGRESS_BG = "#E5E7EB"
                target.PROGRESS_CHUNK = "#0078D4"

                target.STATUS_COLORS.update({
                    'PENDING':   '#605E5C',
                    'MATCHED':   '#107C10',
                    'MULTIPLE':  '#D83B01',
                    'NO_MATCH':  '#A4262C',
                    'UNCERTAIN': '#D97706',
                    'IGNORED':   '#8A8886',
                })

            # Update Semantic Aliases
            target.SUCCESS = target.STATUS_COLORS['MATCHED']
            target.WARNING = target.STATUS_COLORS['MULTIPLE']
            target.ERROR = target.STATUS_COLORS['NO_MATCH']
            target.INFO = target.STATUS_COLORS['LINKED']

