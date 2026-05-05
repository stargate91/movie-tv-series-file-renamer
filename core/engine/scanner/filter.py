import os

class FileFilter:
    """
    Handles file categorization, extension filtering, and asset-to-parent linking logic.
    """
    def __init__(self, settings):
        self.s = settings
        self.video_exts = self._clean_exts(settings.video_extensions)
        self.sub_exts = self._clean_exts(settings.subtitle_extensions)
        self.audio_exts = self._clean_exts(settings.audio_extensions)
        self.img_exts = self._clean_exts(settings.image_extensions)
        self.meta_exts = self._clean_exts(settings.metadata_extensions)

    def _clean_exts(self, s):
        return {("." + e.strip().lower().lstrip(".")) for e in s.split(",") if e.strip()}

    def get_category(self, path):
        """Identifies the media category of a file based on its extension and size."""
        ext = os.path.splitext(path)[1].lower()
        size_mb = os.path.getsize(path) / (1024 * 1024)
        
        if ext in self.video_exts:
            return 'video' if size_mb >= self.s.vid_size else 'extra'
        if ext in self.sub_exts: return 'subtitle'
        if ext in self.audio_exts: return 'audio'
        if ext in self.img_exts: return 'image'
        if ext in self.meta_exts: return 'metadata'
        return 'unknown'

    def get_language(self, path):
        """Detects language from filename using a predefined map of popular languages."""
        name_lower = os.path.basename(path).lower()
        
        # Mapping of ISO codes to common filename keywords
        lang_map = {
            'HUN': ['hun', 'hungarian', 'magyar'],
            'ENG': ['eng', 'english', 'angol'],
            'GER': ['ger', 'german', 'nemet', 'deutsch'],
            'FRA': ['fra', 'french', 'francia', 'fle'],
            'SPA': ['spa', 'spanish', 'spanyol'],
            'ITA': ['ita', 'italian', 'olasz'],
            'RUS': ['rus', 'russian', 'orosz'],
            'JPN': ['jpn', 'japanese', 'japan'],
            'KOR': ['kor', 'korean', 'koreai'],
            'CHI': ['chi', 'chinese', 'kinai'],
            'POR': ['por', 'portuguese', 'portugal'],
            'DUT': ['dut', 'dutch', 'holland']
        }
        
        # Check for keywords with separators to avoid false positives (e.g. "change" containing "eng")
        norm_name = f".{name_lower}.".replace('-', '.').replace('_', '.').replace(' ', '.')
        
        for code, keywords in lang_map.items():
            for k in keywords:
                if f".{k}." in norm_name:
                    return code
        return None

    def get_sub_category(self, path, category):
        """Identifies granular types for extras based on filename keywords."""
        name_lower = os.path.basename(path).lower()
        
        if category == 'extra':
            for k in ['sample', 'minta']: 
                if k in name_lower: return 'sample'
            for k in ['trailer', 'teaser', 'elozetes']:
                if k in name_lower: return 'trailer'
            for k in ['behind the scenes', 'making of', 'kulisszak', 'igy keszult']:
                if k in name_lower: return 'behind the scenes'
            for k in ['deleted', 'kimaradt']:
                if k in name_lower: return 'deleted'
            for k in ['interview', 'interju']:
                if k in name_lower: return 'interview'
            for k in ['featurette']:
                if k in name_lower: return 'featurette'
            return 'bonus'
            
        if category == 'image':
            for k in ['poster', 'plakat']:
                if k in name_lower: return 'poster'
            for k in ['fanart']:
                if k in name_lower: return 'fanart'
            for k in ['background', 'bg', 'backdrop', 'hatter']:
                if k in name_lower: return 'background'
            for k in ['banner']:
                if k in name_lower: return 'banner'
            for k in ['thumb', 'landscape']:
                if k in name_lower: return 'thumb'
            for k in ['logo', 'clearlogo']:
                if k in name_lower: return 'logo'
            for k in ['disc', 'cd']:
                if k in name_lower: return 'disc'
            return 'image'
            
        if category == 'subtitle':
            for k in ['forced', 'kenyszeritett']:
                if k in name_lower: return 'forced'
            for k in ['full', 'teljes']:
                if k in name_lower: return 'full'
            return 'subtitle'
            
        if category == 'audio':
            for k in ['dub', 'szinkron']:
                if k in name_lower: return 'dub'
            for k in ['commentary', 'kommentar']:
                if k in name_lower: return 'commentary'
            for k in ['music', 'ost', 'zene']:
                if k in name_lower: return 'music'
            return 'audio'
            
        return None

