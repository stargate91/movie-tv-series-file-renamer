import re
import logging
from PySide6.QtCore import QThread, Signal, Qt

logger = logging.getLogger(__name__)

class SearchWorker(QThread):
    """
    Handles background API searches for movies, shows, seasons, and episodes.
    """
    results_found = Signal(list, str) # results, mode

    def __init__(self, engine, query, year, search_type, mode="search", parent_id=None, season_num=None):
        super().__init__()
        self.engine = engine
        self.query = query
        self.year = year
        self.search_type = search_type
        self.mode = mode
        self.parent_id = parent_id # tmdb_id of show
        self.season_num = season_num

    def run(self):
        lang = self.engine.config.settings.metadata_language
        try:
            if self.mode == "search":
                # Extract S/E hints from query if any
                s_match = re.search(r'[sS](\d+)', self.query)
                e_match = re.search(r'[eE](\d+)', self.query)
                clean_query = re.sub(r'[sS]\d+|[eE]\d+', '', self.query).strip()
                
                results = self.engine.resolver.matcher.search_api(clean_query, self.year, self.search_type)
                
                # Auto-drill into TV episodes if hints found
                if self.search_type == "tv" and results and (s_match or e_match):
                    best_show = results[0]
                    s_num = int(s_match.group(1)) if s_match else None
                    if s_num is not None:
                        eps_data = self.engine.resolver.matcher.api.get_from_tmdb_season(best_show['tmdb_id'], s_num, language=lang)
                        ep_results = []
                        for ep in eps_data.get('episodes', []):
                            ep_results.append({
                                'tmdb_id': ep['id'],
                                'title': f"S{str(s_num).zfill(2)}E{str(ep['episode_number']).zfill(2)} - {ep['name']}",
                                'media_type': 'episode',
                                'show_id': best_show['tmdb_id'],
                                'season_number': s_num,
                                'episode_number': ep['episode_number'],
                                'poster_path': ep.get('still_path') or best_show.get('poster_path'),
                                'overview': ep.get('overview')
                            })
                        self.results_found.emit(ep_results, "episodes")
                        return

                self.results_found.emit(results, "search")

            elif self.mode == "seasons":
                data = self.engine.resolver.matcher.api.get_from_tmdb_tv_detail(self.parent_id, language=lang)
                results = []
                for s in data.get('seasons', []):
                    results.append({
                        'tmdb_id': s['id'], 'title': s['name'], 'media_type': 'season',
                        'show_id': self.parent_id, 'season_number': s['season_number'],
                        'episode_count': s.get('episode_count'), 'poster_path': s.get('poster_path'),
                        'year': s.get('air_date', '')[:4]
                    })
                self.results_found.emit(results, "seasons")

            elif self.mode == "episodes":
                data = self.engine.resolver.matcher.api.get_from_tmdb_season(self.parent_id, self.season_num, language=lang)
                results = []
                for ep in data.get('episodes', []):
                    results.append({
                        'tmdb_id': ep['id'], 'title': f"E{str(ep['episode_number']).zfill(2)} - {ep['name']}",
                        'media_type': 'episode', 'show_id': self.parent_id,
                        'season_number': self.season_num, 'episode_number': ep['episode_number'],
                        'poster_path': ep.get('still_path'), 'overview': ep.get('overview')
                    })
                self.results_found.emit(results, "episodes")

        except Exception as e:
            logger.error(f"SearchWorker Error: {e}", exc_info=True)
            self.results_found.emit([], "error")
