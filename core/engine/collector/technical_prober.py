import json
import subprocess
import logging

logger = logging.getLogger(__name__)

class TechnicalProber:
    """
    Uses ffprobe to extract technical metadata from video/audio files.
    """
    def probe(self, file_path):
        """Runs ffprobe and returns clean database columns."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-analyzeduration', '10000000',
                '-probesize', '10000000',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
            if result.returncode != 0: return None
            
            data = json.loads(result.stdout)
            return self._parse_json(data)
            
        except Exception as e:
            logger.warning(f"ffprobe error for {file_path}: {e}")
            return None

    def _parse_json(self, data):
        result = {}
        fmt = data.get('format', {})
        streams = data.get('streams', [])
        
        # Duration & Title
        if fmt.get('duration'):
            try: result['duration'] = float(fmt['duration'])
            except: pass
        
        tags = fmt.get('tags', {})
        title = tags.get('title') or tags.get('TITLE')
        if title: result['internal_title'] = title
        
        # Video
        v_streams = [s for s in streams if s.get('codec_type') == 'video']
        if v_streams:
            vs = v_streams[0]
            if vs.get('width') and vs.get('height'):
                result['resolution'] = f"{vs['width']}x{vs['height']}"
            result['video_codec'] = vs.get('codec_name', '').upper()
            if vs.get('bit_rate'):
                try: result['video_bitrate'] = int(vs['bit_rate'])
                except: pass
            fps = vs.get('r_frame_rate', '')
            if '/' in fps:
                try:
                    num, den = map(int, fps.split('/'))
                    result['framerate'] = f"{num/den:.3f}"
                except: result['framerate'] = fps
            if vs.get('bits_per_raw_sample'):
                try: result['bit_depth'] = int(vs['bits_per_raw_sample'])
                except: pass
            result['hdr_type'] = self._detect_hdr(vs)
        
        # Audio & Subtitles (simplified summary + full JSON)
        a_streams = [s for s in streams if s.get('codec_type') == 'audio']
        if a_streams:
            primary = a_streams[0]
            result['audio_codec'] = primary.get('codec_name', '').upper()
            result['audio_channels'] = primary.get('channel_layout', str(primary.get('channels', '')))
            lang = primary.get('tags', {}).get('language', 'und')
            if lang.lower() != 'und': result['language'] = lang.lower()
            
            a_list = []
            for s in a_streams:
                a_list.append({
                    'codec': s.get('codec_name', '').upper(),
                    'channels': s.get('channels'),
                    'language': s.get('tags', {}).get('language', 'und')
                })
            result['audio_streams_json'] = json.dumps(a_list)

        result['technical_json'] = json.dumps(data)
        return result

    def _detect_hdr(self, vs):
        transfer = vs.get('color_transfer', '').lower()
        side_data = vs.get('side_data_list', [])
        for sd in side_data:
            if 'dovi' in sd.get('side_data_type', '').lower(): return 'Dolby Vision'
        if 'smpte2084' in transfer or 'st2084' in transfer: return 'HDR10'
        if 'arib-std-b67' in transfer: return 'HLG'
        return 'SDR'
