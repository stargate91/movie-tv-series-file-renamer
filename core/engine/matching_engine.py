import re
import json
import logging
import unicodedata
from api.client import APIClient

logger = logging.getLogger(__name__)

class MatchingEngine:
    """
    Handles search logic and confidence evaluation for matching files to TMDB.
    Responsible for:
    - Executing API searches (title, year, type).
    - Evaluating result confidence.
    - Normalizing text for comparisons.
    - Waterfall search sequence.
    """

    def __init__(self, db, settings):
        self.db = db
        self.s = settings
        self.api = APIClient(
            omdb_key=settings.omdb_key,
            tmdb_key=settings.tmdb_key,
            tmdb_bearer_token=settings.tmdb_bearer_token,
            db=self.db
        )

    @property
    def language(self):
        return getattr(self.s, 'metadata_language', 'en-US')

    @property
    def fallback_language(self):
        return getattr(self.s, 'fallback_language', '')

    def resolve_by_imdb(self, imdb_id, language_override=None):
        """Uses /find endpoint to get TMDB data from IMDB ID. Always trusted."""
        try:
            target_lang = language_override or self.language
            data = self.api.get_external_id_raw(imdb_id, language=target_lang)
            if not data: return None
            
            movies = data.get('movie_results', [])
            if movies:
                m = movies[0]
                return {
                    'tmdb_id': m['id'],
                    'imdb_id': imdb_id,
                    'title': m.get('title', ''),
                    'year': self._extract_year(m.get('release_date', '')),
                    'media_type': 'movie',
                    'poster_path': m.get('poster_path'),
                    'details_json': json.dumps(m, ensure_ascii=False)
                }
            
            tv = data.get('tv_results', [])
            if tv:
                t = tv[0]
                return {
                    'tmdb_id': t['id'],
                    'imdb_id': imdb_id,
                    'title': t.get('name', ''),
                    'year': self._extract_year(t.get('first_air_date', '')),
                    'media_type': 'tv',
                    'poster_path': t.get('poster_path'),
                    'details_json': json.dumps(t, ensure_ascii=False)
                }
        except Exception as e:
            logger.warning(f"IMDB resolve failed for {imdb_id}: {e}")
        return None

    def search_api(self, title, year, search_type, language_override=None):
        """Searches TMDB by title+year. Returns list of result dicts."""
        target_lang = language_override or self.language
        results = self._execute_search(title, year, search_type, target_lang)
        
        if not results and self.fallback_language:
            logger.debug(f"No results for '{title}' in {target_lang}, trying fallback {self.fallback_language}")
            results = self._execute_search(title, year, search_type, self.fallback_language)
            
        return results

    def _execute_search(self, title, year, search_type, language):
        """Helper to perform the actual API call with a specific language."""
        results = []
        year_str = str(year) if year else "unknown"
        
        try:
            if search_type in ('movie', None):
                data = self.api.search_movie(title, year_str, language)
                for r in data.get('results', [])[:20]:
                    results.append({
                        'tmdb_id': r['id'],
                        'title': r.get('title', ''),
                        'original_title': r.get('original_title', ''),
                        'year': self._extract_year(r.get('release_date', '')),
                        'media_type': 'movie',
                        'poster_path': r.get('poster_path'),
                        'details_json': json.dumps(r, ensure_ascii=False)
                    })
            
            if search_type in ('episode', 'tv', None):
                data = self.api.search_tv(title, year_str, language)
                for r in data.get('results', [])[:20]:
                    results.append({
                        'tmdb_id': r['id'],
                        'title': r.get('name', ''),
                        'original_title': r.get('original_name', ''),
                        'year': self._extract_year(r.get('first_air_date', '')),
                        'media_type': 'tv',
                        'poster_path': r.get('poster_path'),
                        'details_json': json.dumps(r, ensure_ascii=False)
                    })
        except Exception as e:
            logger.warning(f"API Search error for '{title}' in {language}: {e}")
        
        return results

    def confidence_check(self, result, search_title, search_year):
        """
        Returns (is_confident, is_super_confident).
        Super confident means exact title (normalized) AND exact year.
        Checks against both translated and original titles.
        """
        result_title = result.get('title', '')
        original_title = result.get('original_title', '')
        result_year = result.get('year')
        
        norm_search = self._normalize(search_title)
        norm_result = self._normalize(result_title)
        norm_original = self._normalize(original_title)
        
        if not norm_search or (not norm_result and not norm_original):
            return False, False
        
        # Title check: normalized containment
        title_exact = (norm_search == norm_result) or (norm_search == norm_original)
        title_ok = title_exact or \
                  (norm_search in norm_result) or (norm_result in norm_search) or \
                  (norm_search in norm_original) or (norm_original in norm_search)
        
        # Exact year match
        exact_year = str(search_year) == str(result_year) if search_year and result_year else False
        
        # Super confident: Exact title AND Exact year
        if title_exact and exact_year:
            return True, True

        # If year is a perfect match, we require at least some title similarity 
        if exact_year and title_ok:
            return True, False
            
        if not title_ok:
            return False, False
        
        # If titles match but year is off, allow max 1 year difference (e.g. 2022 vs 2023 release)
        if search_year and result_year:
            try:
                if abs(int(search_year) - int(result_year)) > 1:
                    return False, False
            except (ValueError, TypeError):
                pass
        
        return True, False

    def _normalize(self, text):
        """Normalizes text for comparison."""
        if not text:
            return ''
        # Remove accents
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        # Lowercase, remove special chars
        text = re.sub(r'[^a-z0-9\s]', '', text.lower())
        # Collapse multiple spaces and strip
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text

    def _extract_year(self, date_str):
        """Extracts year from date string."""
        if date_str and len(date_str) >= 4:
            try: return int(date_str[:4])
            except ValueError: pass
        return None

    def guess_search_type(self, vid):
        """Guesses media type."""
        if vid.get('fn_season') is not None or vid.get('fd_season') is not None:
            return 'episode'
        if vid.get('fn_media_type') == 'episode' or vid.get('fd_media_type') == 'episode':
            return 'episode'
        return None

    def parse_title_year(self, raw_title):
        """Splits 'Title (2006)'."""
        match = re.match(r'(.+?)\s*\((\d{4})\)\s*$', raw_title)
        if match:
            return match.group(1).strip(), int(match.group(2))
        return raw_title.strip(), None

    def get_all_search_terms(self, vid):
        """Yields all available (title, year, source) tuples."""
        if vid.get('internal_title'):
            title, year = self.parse_title_year(vid['internal_title'])
            if title: yield (title, year, 'internal_title')
        if vid.get('fn_title'):
            yield (vid['fn_title'], vid.get('fn_year'), 'filename')
        if vid.get('fd_title'):
            yield (vid['fd_title'], vid.get('fd_year'), 'foldername')
