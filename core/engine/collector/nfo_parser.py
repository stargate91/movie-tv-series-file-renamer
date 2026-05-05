import re
import logging

logger = logging.getLogger(__name__)

class NFOParser:
    """
    Extracts IMDB IDs and other metadata from .nfo files.
    Supports Kodi XML and plain text formats.
    """
    def parse_file(self, nfo_path):
        """Extracts an IMDB ID from an .nfo file."""
        try:
            content = self._read_safe(nfo_path)
            if not content: return None

            # Pattern 1: Kodi XML <uniqueid type="imdb">tt1234567</uniqueid>
            match = re.search(r'<uniqueid[^>]*type=["\']imdb["\'][^>]*>(tt\d+)</uniqueid>', content, re.IGNORECASE)
            if match: return match.group(1)
            
            # Pattern 2: XML tags <imdbid> or <id>
            match = re.search(r'<(?:imdbid|imdb|id)>(tt\d+)</(?:imdbid|imdb|id)>', content, re.IGNORECASE)
            if match: return match.group(1)

            # Pattern 3: URL
            match = re.search(r'imdb\.com/title/(tt\d+)', content, re.IGNORECASE)
            if match: return match.group(1)
            
            # Pattern 4: Bare tt ID
            match = re.search(r'\b(tt\d{7,})\b', content)
            if match: return match.group(1)

        except Exception as e:
            logger.warning(f"NFO parse error for {nfo_path}: {e}")
        return None

    def _read_safe(self, path):
        """Tries multiple encodings to read the file."""
        for enc in ('utf-8', 'latin-1', 'cp1250'):
            try:
                with open(path, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        return None
