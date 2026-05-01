import os
import re
import logging

logger = logging.getLogger(__name__)

class MetadataDiscovery:
    """Discovers IDs and Titles from NFO files and Internal Media Metadata."""
    
    def __init__(self):
        self.imdb_pattern = re.compile(r'tt\d{7,8}')
        self.tmdb_pattern = re.compile(r'themoviedb\.org/(movie|tv)/(\d+)')
        
        try:
            from pymediainfo import MediaInfo
            self.MediaInfo = MediaInfo
            self.has_mediainfo = MediaInfo.can_parse()
        except ImportError:
            self.MediaInfo = None
            self.has_mediainfo = False
            logger.warning("pymediainfo not installed. Internal metadata discovery disabled.")

    def discover(self, file_paths, ui=None):
        """Discovers metadata for a list of files."""
        results = {}
        total = len(file_paths)
        
        for i, path in enumerate(file_paths):
            if ui: ui.update_progress(i + 1, total, f"Analyzing: {os.path.basename(path)}")
            
            discovery_data = {
                'imdb_id': None,
                'tmdb_id': None,
                'internal_title': None,
                'source_nfo': None,
                'technical': {} # Resolution, Codecs, etc.
            }
            
            # 1. Search for NFO
            nfo_path = self._find_nfo(path)
            if nfo_path:
                ids = self._parse_nfo(nfo_path)
                discovery_data.update(ids)
                discovery_data['source_nfo'] = nfo_path
            
            # 2. Search Internal Metadata (Technical + Title)
            if self.has_mediainfo:
                media_info = self._get_media_info(path)
                if media_info:
                    discovery_data['internal_title'] = media_info.get('title')
                    discovery_data['technical'] = media_info.get('technical', {})
            
            # Fallback to FFmpeg if internal_title is still missing
            if not discovery_data['internal_title']:
                discovery_data['internal_title'] = self._get_ffmpeg_title(path)

            # 3. Quick filename check for Part/CD (to be extra safe)
            import guessit
            g = guessit.guessit(os.path.basename(path))
            p_val = g.get('part') or g.get('cd')
            if p_val:
                discovery_data['part'] = f"CD{p_val}"
            
            # Only add if we found something (IDs, Title, Technical OR Part info)
            if any([discovery_data['imdb_id'], discovery_data['tmdb_id'], discovery_data['internal_title'], discovery_data['technical'], discovery_data.get('part')]):
                results[path] = discovery_data
                
        return results

    def _get_ffmpeg_title(self, path):
        """Extracts title tag using ffmpeg-python."""
        try:
            import ffmpeg
            probe = ffmpeg.probe(path)
            # Check format tags
            tags = probe.get('format', {}).get('tags', {})
            title = tags.get('title')
            if title and len(title) > 2:
                # Basic filter
                if title.strip().upper() not in ["SDR RELEASE", "BAKER-RLS"]:
                    return title
        except Exception:
            pass
        return None

    def _find_nfo(self, video_path):
        """Looks for an NFO file with the same name or in the same directory."""
        base_dir = os.path.dirname(video_path)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # Priority 1: Same filename.nfo
        p1 = os.path.join(base_dir, f"{base_name}.nfo")
        if os.path.exists(p1): return p1
        
        # Priority 2: Any .nfo in the same directory (if only one exists)
        nfos = [f for f in os.listdir(base_dir) if f.lower().endswith('.nfo')]
        if len(nfos) == 1:
            return os.path.join(base_dir, nfos[0])
            
        return None

    def _parse_nfo(self, nfo_path):
        """Extracts IDs and Type from NFO content."""
        results = {'imdb_id': None, 'tmdb_id': None, 'nfo_type': None}
        try:
            with open(nfo_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                imdb = self.imdb_pattern.search(content)
                tmdb = self.tmdb_pattern.search(content)
                
                if imdb: results['imdb_id'] = imdb.group(0)
                if tmdb: results['tmdb_id'] = tmdb.group(2)
                
                # Type detection based on XML tags
                low_content = content.lower()
                if '<movie' in low_content:
                    results['nfo_type'] = 'movie'
                elif '<tvshow' in low_content or '<episodedetails' in low_content:
                    results['nfo_type'] = 'episode'
        except Exception as e:
            logger.error(f"Error parsing NFO {nfo_path}: {e}")
            
        return results

    def _get_media_info(self, video_path):
        """Extracts internal title and technical specs from the video file."""
        try:
            info = self.MediaInfo.parse(video_path)
            res = {'title': None, 'technical': {}}
            tech = res['technical']
            
            for track in info.tracks:
                if track.track_type == 'General':
                    if track.title and len(track.title) > 2:
                        if track.title.strip().upper() not in ["SDR RELEASE", "BAKER-RLS"]:
                            res['title'] = track.title
                
                elif track.track_type == 'Video':
                    tech['vcodec'] = track.format
                    tech['width'] = track.width
                    tech['height'] = track.height
                    # Heuristic for resolution label
                    if track.height:
                        if track.height >= 2160: tech['resolution'] = '2160p'
                        elif track.height >= 1080: tech['resolution'] = '1080p'
                        elif track.height >= 720: tech['resolution'] = '720p'
                        else: tech['resolution'] = f"{track.height}p"

                elif track.track_type == 'Audio' and 'acodec' not in tech:
                    tech['acodec'] = track.format
                    tech['channels'] = track.channel_s
                    
                elif track.track_type == 'Text':
                    if 'subs' not in tech: tech['subs'] = []
                    if track.language:
                        tech['subs'].append(track.language)

            return res
        except Exception as e:
            logger.error(f"Error reading internal metadata for {video_path}: {e}")
            
        return None
