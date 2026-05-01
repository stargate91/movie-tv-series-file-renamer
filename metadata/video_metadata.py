import ffmpeg
import logging
import os
from utils.cache import DataStore

logger = logging.getLogger(__name__)

def get_video_metadata(file_path):
    """
    Extracts technical metadata from a video file using a single ffprobe call.
    Uses a persistent cache to avoid re-probing unchanged files.
    """
    if not os.path.exists(file_path):
        return {}

    # 1. Check Cache first
    tech_cache = DataStore("tech_metadata_cache")
    try:
        mtime = os.path.getmtime(file_path)
        fsize = os.path.getsize(file_path)
        # Unique key based on path, size and time
        cache_key = f"{file_path}_{fsize}_{mtime}"
    except:
        cache_key = file_path

    cached_data = tech_cache.get(cache_key)
    if cached_data:
        return cached_data

    # 2. If not in cache, run ffprobe
    metadata = {
        "resolution": "Unknown",
        "video_codec": "Unknown",
        "video_bitrate": "Unknown",
        "framerate": "Unknown",
        "hdr_type": "None",
        "bit_depth": "Unknown",
        "audio_codec": "Unknown",
        "audio_channels": "Unknown",
        "audio_channels_description": "Unknown",
        "first_audio_channel_language": "Unknown",
        "audio_streams_count": 0,
        "subtitle_languages": "None"
    }

    try:
        probe = ffmpeg.probe(file_path)
        
        # --- VIDEO STREAM ---
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        if video_stream:
            width = video_stream.get('width')
            height = video_stream.get('height')
            if width and height:
                if width >= 3840: metadata["resolution"] = "4K"
                elif width >= 1920: metadata["resolution"] = "1080p"
                elif width >= 1280: metadata["resolution"] = "720p"
                else: metadata["resolution"] = f"{height}p"

            metadata["video_codec"] = video_stream.get('codec_name', 'Unknown').upper()
            
            # Bitrate
            bitrate = video_stream.get('bit_rate') or probe.get('format', {}).get('bit_rate')
            if bitrate:
                metadata["video_bitrate"] = f"{int(bitrate) // 1000} kbps"
            
            # Framerate
            fps_raw = video_stream.get('avg_frame_rate', '0/0')
            if '/' in fps_raw:
                try:
                    num, den = map(int, fps_raw.split('/'))
                    if den != 0:
                        metadata["framerate"] = f"{round(num / den, 2)} fps"
                except: pass

            # HDR and Bit Depth
            pix_fmt = video_stream.get('pix_fmt', '')
            metadata["bit_depth"] = f"{video_stream.get('bits_per_raw_sample', '8')} bit"
            
            color_space = video_stream.get('color_space', '')
            color_transfer = video_stream.get('color_transfer', '')
            if 'bt2020' in color_space or 'smpte2084' in color_transfer:
                metadata["hdr_type"] = "HDR10"
                if 'arib-std-b67' in color_transfer: metadata["hdr_type"] = "HLG"
            elif 'dolby' in video_stream.get('codec_name', '').lower():
                metadata["hdr_type"] = "Dolby Vision"

        # --- AUDIO STREAMS ---
        audio_streams = [s for s in probe['streams'] if s['codec_type'] == 'audio']
        metadata["audio_streams_count"] = len(audio_streams)
        
        if audio_streams:
            first_audio = audio_streams[0]
            metadata["audio_codec"] = first_audio.get('codec_name', 'Unknown').upper()
            channels = first_audio.get('channels', 0)
            metadata["audio_channels"] = str(channels)
            
            if channels >= 8: metadata["audio_channels_description"] = "7.1"
            elif channels >= 6: metadata["audio_channels_description"] = "5.1"
            elif channels >= 2: metadata["audio_channels_description"] = "Stereo"
            else: metadata["audio_channels_description"] = "Mono"
            
            lang = first_audio.get('tags', {}).get('language', 'Unknown')
            import pycountry
            try:
                c = pycountry.languages.get(alpha_3=lang)
                metadata["first_audio_channel_language"] = c.name if c else lang
            except:
                metadata["first_audio_channel_language"] = lang

        # --- SUBTITLES ---
        subs = [s for s in probe['streams'] if s['codec_type'] == 'subtitle']
        sub_langs = []
        import pycountry
        for s in subs:
            l = s.get('tags', {}).get('language')
            if l:
                try:
                    c = pycountry.languages.get(alpha_3=l)
                    sub_langs.append(c.name if c else l)
                except: sub_langs.append(l)
        
        if sub_langs:
            metadata["subtitle_languages"] = ", ".join(sorted(list(set(sub_langs))))

        # Save to Cache before returning
        tech_cache.set(cache_key, metadata)

    except Exception as e:
        logger.error(f"FFprobe error for {file_path}: {e}")
        
    return metadata