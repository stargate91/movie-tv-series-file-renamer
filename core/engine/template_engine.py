import re
import logging

logger = logging.getLogger(__name__)

class TemplateEngine:
    """
    Handles template parsing, tag replacement, and filename sanitization.
    Responsible for:
    - Replacing {Tags} with values.
    - Applying casing (Title, lower, UPPER).
    - Handling word separators (dot, dash, underscore).
    - Cleaning up empty brackets and artifacts.
    - Sanitizing illegal characters for the file system.
    """

    def _smart_title(self, text):
        """Title cases text while preserving Roman Numerals and Acronyms."""
        if not text: return ""
        
        # Standard title case
        text = text.title()
        
        # Restore Roman Numerals (Common ones: I, II, III, IV, V, VI, VII, VIII, IX, X)
        def restore_roman(match):
            word = match.group(0)
            # if it looks like a mangled roman numeral (e.g. Iv, Iii, Vi)
            roman_map = {
                "I": "I", "Ii": "II", "Iii": "III", "Iv": "IV", "V": "V",
                "Vi": "VI", "Vii": "VII", "Viii": "VIII", "Ix": "IX", "X": "X"
            }
            return roman_map.get(word, word)
            
        return re.sub(r'\b(I|Ii|Iii|Iv|V|Vi|Vii|Viii|Ix|X)\b', restore_roman, text)

    def process(self, template, context, settings):
        """Processes a template string into a formatted filename."""
        formatted_name = template
        c_low = settings.filename_case.lower() if settings.filename_case else "none"
        
        # Tags that should be protected from Title Case mangling
        protected_tags = {"Language", "Resolution", "VideoCodec", "AudioCodec", 
                          "ParentName", "HDR", "BitDepth", "TMDB_ID", "IMDB_ID",
                          "SeriesResolution", "SeasonResolution", "Original"}
                          
        for tag, value in context.items():
            if not value:
                formatted_name = formatted_name.replace(f"{{{tag}}}", "")
                continue
            
            val_str = str(value)
            if c_low == "title" and tag not in protected_tags:
                val_str = self._smart_title(val_str)
            formatted_name = formatted_name.replace(f"{{{tag}}}", val_str)

        # 1. Cleanup artifacts
        formatted_name = self.cleanup_empty_tags(formatted_name)
        
        # 2. Apply global casing
        if c_low == "lower": formatted_name = formatted_name.lower()
        elif c_low == "upper": formatted_name = formatted_name.upper()
            
        # 3. Apply separator
        formatted_name = self.apply_separator(formatted_name, settings.separator)
        
        # 4. Final sanitization
        return self.sanitize_filename(formatted_name)

    def cleanup_empty_tags(self, text):
        """Cleans up leftover formatting when variables are empty."""
        text = re.sub(r'\{[^}]+\}', '', text)
        text = re.sub(r'\[\s*\]', '', text)
        text = re.sub(r'\(\s*\)', '', text)
        text = re.sub(r'\{\s*\}', '', text)
        text = re.sub(r'(\s*-\s*){2,}', ' - ', text)
        text = re.sub(r'\s+-\s+$', '', text)
        text = re.sub(r'^\s+-\s+', '', text)
        text = re.sub(r'\s+-\s+(?=\.)', '', text)
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text

    def sanitize_filename(self, text):
        """Removes characters that are illegal in Windows file/folder names."""
        # Windows forbidden: : * ? " < > | / \
        illegal_chars = ':*?"<>|/\\'
        for ch in illegal_chars:
            text = text.replace(ch, ' ')
        # Clean up any double spaces created by replacement
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text

    def apply_separator(self, text, separator):
        sep_map = {"space": " ", "dot": ".", "dash": "-", "underscore": "_", "none": ""}
        separator = sep_map.get(separator.lower(), separator) if separator else " "
        if separator == " " or not separator: return text
        if separator in [".", "_"]:
            text = re.sub(r'[\[\]\(\)\{\}]', '', text)
            text = re.sub(r'\s+-\s+', separator, text)
        text = text.replace(" ", separator)
        escaped_sep = re.escape(separator)
        text = re.sub(f'{escaped_sep}{{2,}}', separator, text)
        return text.strip(separator)
