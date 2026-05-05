import json
import os
import logging
import re
from core.constants import RESOLUTION_MAP, VIDEO_CODEC_MAP, AUDIO_CODEC_MAP, AUDIO_CHANNELS_MAP

logger = logging.getLogger(__name__)

class TagBuilder:
    """
    Constructs the metadata context (dictionary of tags) for a file.
    Fetches technical data from file_data and cultural/media data from the database.
    """

    def __init__(self, db):
        self.db = db

    def build_context(self, file_data, links, custom_variable=""):
        """Main entry point to construct the dictionary of variables."""
        context = {}
        
        # 1. Base / Technical Tags
        self._add_technical_tags(context, file_data, custom_variable)
        
        # 2. Accumulate data from all linked media items
        media_data = self._collect_media_data(links)
        
        # 3. Add Media & TV Tags
        self._add_media_tags(context, media_data)
        
        # 4. Handle TV specific logic (Seasons, Episodes)
        if any(m['media_type'] == 'tv' for m in media_data['items']):
            self._add_tv_tags(context, media_data, file_data)

        # 5. Final Calculation (Titles, Merging)
        self._add_final_tags(context, media_data)

        return context

    # ── Tag Providers ───────────────────────────────────────────

    def _add_technical_tags(self, context, file_data, custom_variable):
        """Extracts and maps technical metadata from the file record."""
        cat = file_data.get("category", "")
        sub_cat = file_data.get("sub_category", "")
        
        context.update({
            "Resolution": self._map_resolution(file_data.get("resolution", "")),
            "VideoCodec": self._map_video_codec(file_data.get("video_codec", "")),
            "AudioCodec": self._map_audio_codec(file_data.get("audio_codec", "")),
            "AudioChannels": self._map_audio_channels(file_data.get("audio_channels", "")),
            "HDR": file_data.get("hdr_type", "") if file_data.get("hdr_type") != "SDR" else "",
            "BitDepth": f"{file_data.get('bit_depth')}bit" if file_data.get("bit_depth") else "",
            "Framerate": file_data.get("framerate", ""),
            "Original": os.path.splitext(file_data.get("file_name", ""))[0],
            "Language": (file_data.get("language") or "").upper() if cat != "video" else "",
            "ExtraCategory": (sub_cat or cat).capitalize() if cat not in ("video", None) else "",
            "Category": cat.capitalize() if cat else "",
            "SubType": sub_cat.capitalize() if sub_cat else "",
            "Custom": custom_variable,
            "VideoBitrate": f"{file_data['video_bitrate'] // 1000}kbps" if file_data.get('video_bitrate') else "",
            "Edition": file_data.get("edition", ""),
        })

    def _collect_media_data(self, links):
        """Fetches and organizes raw data from media_items and tv_episodes."""
        data = {
            'items': [], 'episodes': [], 
            'titles': [], 'years': [], 'tmdb_ids': [], 'imdb_ids': [],
            'ep_titles': [], 'seasons': [], 'ep_nums': [], 'show_titles': []
        }
        
        for link in links:
            media = self.db.media.get_media_item_by_id(link['media_item_id'])
            if not media: continue
            
            data['items'].append(media)
            data['titles'].append(media['title'])
            if media.get('year'): data['years'].append(str(media['year']))
            if media.get('tmdb_id'): data['tmdb_ids'].append(f"tmdb-{media['tmdb_id']}")
            if media.get('imdb_id'): data['imdb_ids'].append(media['imdb_id'])
            
            if media['media_type'] == 'tv':
                data['show_titles'].append(media['title'])
                if link.get('tv_episode_id'):
                    ep = self.db.media.get_episode_by_id(link['tv_episode_id'])
                    if ep:
                        data['episodes'].append(ep)
                        data['seasons'].append(ep['season_number'])
                        data['ep_nums'].append(ep['episode_number'])
                        if ep.get('name'): data['ep_titles'].append(ep['name'])
        return data

    def _add_media_tags(self, context, media_data):
        """Adds global metadata from the primary (or first) media item."""
        if not media_data['items']: return
        
        # We take global info from the first linked item
        m = media_data['items'][0]
        context.update({
            "Director": m.get('director', ""),
            "Cast": m.get('cast', ""),
            "RatingTmdb": m.get('rating_tmdb', ""),
            "RatingImdb": m.get('rating_imdb', ""),
            "RatingRotten": m.get('rating_rotten', ""),
            "RatingMetacritic": m.get('rating_metacritic', ""),
            "Budget": f"${m['budget']:,}" if m.get('budget') else "",
            "Revenue": f"${m['revenue']:,}" if m.get('revenue') else "",
            "Runtime": f"{m['runtime']} min" if m.get('runtime') else "",
            "Genres": m.get('genres', ""),
            "Tagline": m.get('tagline', ""),
            "Popularity": m.get('popularity', ""),
            "OriginalTitle": m.get('original_title', ""),
            "OriginalLanguage": (m.get('original_language') or "").upper(),
            "Languages": m.get('languages', ""),
            "ReleaseDate": m.get('release_date') or m.get('first_air_date', ""),
        })

    def _add_tv_tags(self, context, media_data, file_data):
        """Adds TV-specific tags (Series, Seasons, Episodes)."""
        # Primary TV Info
        tv_items = [m for m in media_data['items'] if m['media_type'] == 'tv']
        if not tv_items: return
        
        m = tv_items[0]
        context.update({
            "SeriesTitle": m['title'],
            "SeriesRating": m.get('rating_imdb') or m.get('rating_tmdb', ""),
            "EpisodeCount": m.get('number_of_episodes', ""),
            "SeasonCount": m.get('number_of_seasons', ""),
            "SeriesOriginalTitle": m.get('original_title', ""),
        })
        
        # Air Years
        f_year, l_year = "", ""
        if m.get('first_air_date'): f_year = m['first_air_date'].split("-")[0]
        if m.get('last_air_date'): l_year = m['last_air_date'].split("-")[0]
        context["FirstAirYear"] = f_year
        context["LastAirYear"] = l_year
        
        status = (m.get('status') or "").lower()
        if status == "ended" and f_year and l_year: context["YearRange"] = f"{f_year}-{l_year}"
        elif f_year: context["YearRange"] = f"{f_year}-"
        else: context["YearRange"] = ""
        
        context["SeriesResolution"] = self.get_series_resolution(m['id'])

        # Season/Episode logic
        seasons = media_data['seasons']
        episodes = media_data['ep_nums']
        
        # Fallback to filename guessing if not linked to specific episodes
        if not seasons:
            s_val = file_data.get("fn_season") if file_data.get("fn_season") is not None else file_data.get("fd_season")
            seasons = [s_val if s_val is not None else 1]
            
        if not episodes:
            e_val = file_data.get("fn_episode") if file_data.get("fn_episode") is not None else file_data.get("fd_episode")
            episodes = self._parse_ep_list(e_val if e_val is not None else 1)

        context["Season"] = self._format_list(seasons, "S")
        context["Episode"] = self._format_list(episodes, "E")
        context["EpisodeTitle"] = self._merge(media_data['ep_titles'])

        # Season enrichment (from TMDB details)
        if seasons:
            self._enrich_season_info(context, m, seasons[0])

        # Specific Episode Tags
        if media_data['episodes']:
            ep = media_data['episodes'][0]
            context.update({
                "EpisodeTMDB_ID": ep.get('tmdb_id', ""),
                "EpisodeIMDB_ID": ep.get('imdb_id', ""),
                "EpisodeRating": ep.get('vote_average', ""),
                "EpisodeRatingImdb": ep.get('rating_imdb', ""),
                "EpisodeRuntime": f"{ep['runtime']} min" if ep.get('runtime') else "",
                "EpisodeAirDate": ep.get('air_date', ""),
                "EpisodeAirYear": ep['air_date'].split("-")[0] if ep.get('air_date') else ""
            })

    def _add_final_tags(self, context, media_data):
        """Finalizes titles and merging multi-item lists."""
        context["Title"] = self._merge(media_data['titles'])
        context["Year"] = self._merge(media_data['years'], sep=", ")
        context["TMDB_ID"] = self._merge(media_data['tmdb_ids'])
        context["IMDB_ID"] = self._merge(media_data['imdb_ids'])
        
        if media_data['show_titles']:
            context["ShowTitle"] = self._merge(media_data['show_titles'])
            context["Title"] = "" # Avoid "Movie Title" tag for TV shows

    # ── Helpers ─────────────────────────────────────────────────

    def _enrich_season_info(self, context, media, season_num):
        """Fetches season-level metadata from the stored JSON details."""
        try:
            if not media.get('details_json'): return
            details = json.loads(media['details_json'])
            s_list = details.get('seasons', [])
            s_data = next((s for s in s_list if s.get('season_number') == season_num), None)
            if s_data:
                context["SeasonName"] = s_data.get('name', f"Season {season_num}")
                context["SeasonEpisodeCount"] = s_data.get('episode_count', "")
                s_air = s_data.get('air_date', "")
                context["SeasonAirDate"] = s_air
                context["SeasonAirYear"] = s_air.split("-")[0] if "-" in s_air else ""
                context["SeasonResolution"] = self.get_series_resolution(media['id'], season_num)
        except: pass

    def _merge(self, items, sep=" & "):
        if not items: return ""
        seen = set()
        return sep.join([str(x) for x in items if x and not (x in seen or seen.add(x))])

    def _parse_ep_list(self, val):
        if isinstance(val, (list, tuple)): return list(val)
        if isinstance(val, str) and val.startswith('['):
            import ast
            try: return ast.literal_eval(val)
            except: pass
        return [val]

    def _format_list(self, nums, prefix):
        if not nums: return ""
        try:
            seen = set()
            unique = sorted([int(x) for x in nums if x is not None and not (x in seen or seen.add(x))])
            if not unique: return ""
            if len(unique) == 1: return f"{prefix}{unique[0]:02d}"
            return "-".join([f"{prefix}{x:02d}" for x in unique])
        except: return str(nums[0]) if nums else ""

    # ── Mappers ─────────────────────────────────────────────────

    def _map_resolution(self, res_str):
        if not res_str or "x" not in res_str: return res_str
        try:
            width, height = map(int, res_str.split("x"))
            if width >= 3800: return "4K"
            for std_h, name in RESOLUTION_MAP.items():
                if abs(height - std_h) <= 50: return name
            return f"{height}p"
        except: return res_str

    def _map_video_codec(self, codec):
        return VIDEO_CODEC_MAP.get(codec.upper(), codec) if codec else ""

    def _map_audio_codec(self, codec):
        return AUDIO_CODEC_MAP.get(codec.upper(), codec) if codec else ""

    def _map_audio_channels(self, channels):
        return AUDIO_CHANNELS_MAP.get(str(channels), str(channels)) if channels else ""

    def get_series_resolution(self, media_item_id, season_number=None):
        """Calculates resolution across a series or specific season."""
        try:
            raw_resolutions = self.db.files.get_resolutions_for_media(media_item_id, season_number)
            resolutions = {self._map_resolution(r) for r in raw_resolutions if r}
            if not resolutions: return ""
            
            res_order = {"4K": 4, "1080p": 3, "720p": 2, "576p": 1, "480p": 0}
            sorted_res = sorted(list(resolutions), key=lambda x: res_order.get(x, -1))
            if len(sorted_res) == 1: return sorted_res[0]
            if len(sorted_res) == 2: return f"{sorted_res[0]}-{sorted_res[1]}"
            return "Mixed"
        except: return "Mixed"
