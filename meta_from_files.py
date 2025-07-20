import pycountry
import ffmpeg

def get_res(file_path):
    try:
        probe = ffmpeg.probe(file_path, v='error', select_streams='v:0', show_entries='stream=width,height')
        stream = probe['streams'][0]
        width = stream['width']
        height = stream['height']

        resolution_map = {
            (1920, 1080): '1080p',
            (1280, 720): '720p',
            (640, 480): '480p',
            (3840, 2160): '4K',
            (2560, 1440): '1440p',
            (720, 480): '480p',
            (720, 576): '576p'
        }

        return resolution_map.get((width, height), f'{width}x{height}')
    
    except ffmpeg._run.Error as e:
        print(f"[ERROR] Error getting resolution for {file_path}: {e}")
        return "unknown"

def get_codec(file_path):
    try:
        probe = ffmpeg.probe(file_path, v='error', select_streams='v:0', show_entries='stream=codec_name')
        codec = probe['streams'][0]['codec_name']

        codec_map = {
            'h264': 'H.264',
            'hevc': 'H.265',
            'vp9': 'VP9',
            'av1': 'AV1',
            'mpeg2video': 'MPEG-2'
        }
        return codec_map.get(codec, codec)

    except ffmpeg._run.Error as e:
        print(f"Error while probing codec for {file_path}: {e}")
        return "unknown"


def get_audio_codec(file_path):
    try:
        probe = ffmpeg.probe(
            file_path,
            v='error',
            select_streams='a:0',
            show_entries='stream=codec_name',
            of='json'
        )
        codec = probe['streams'][0]['codec_name']
        codec_map = {
            'aac': 'AAC',
            'ac3': 'Dolby Digital',
            'dts': 'DTS',
            'dtshd': 'DTS-HD',
            'eac3': 'Dolby Digital Plus',
            'mp3': 'MP3',
            'flac': 'FLAC',
            'opus': 'Opus',
            'vorbis': 'Vorbis',
            'truehd': 'TrueHD'
        }
        return codec_map.get(codec, codec)
    except Exception as e:
        print(f"Error reading audio codec for {file_path}: {e}")
        return "unknown"


def get_video_bitrate(file_path):
    try:
        probe = ffmpeg.probe(
            file_path,
            v='error',
            select_streams='v:0',
            show_entries='stream=bit_rate',
            of='json'
        )
        bitrate_str = probe['streams'][0].get('bit_rate')
        if bitrate_str:
            bitrate_bps = int(bitrate_str)
            bitrate_mbps = bitrate_bps / 1_000_000
            return f"{bitrate_mbps:.2f} mbps"
        else:
            return "unknown"
    except Exception as e:
        print(f"Error reading video bitrate for {file_path}: {e}")
        return "unknown"

def get_framerate(file_path):
    try:
        probe = ffmpeg.probe(
            file_path, 
            select_streams='v:0', 
            show_entries='stream=r_frame_rate', 
            v='error'
        )
        fr_str = probe['streams'][0]['r_frame_rate']  # pl. '30000/1001'
        num, den = map(int, fr_str.split('/'))
        framerate = round(num / den, 2)
        return f"{framerate} fps"
    except Exception as e:
        print(f"Error getting framerate for {file_path}: {e}")
        return "unknown"

def get_audio_channels(file_path):
    channel_map = {
        1: "Mono",
        2: "Stereo",
        6: "5.1",
        8: "7.1"
    }
    try:
        probe = ffmpeg.probe(
            file_path,
            v='error',
            select_streams='a:0',
            show_entries='stream=channels',
            of='json'
        )
        channels = probe['streams'][0].get('channels')
        if channels is None:
            return "unknown"
        return channel_map.get(channels, f"{channels}-ch")
    except Exception as e:
        print(f"Error reading audio channels for {file_path}: {e}")
        return "unknown"

def get_language_code_2(lang_name_or_code):
    if not lang_name_or_code:
        return "unknown"
    
    lang_input = lang_name_or_code.strip().lower()

    if len(lang_input) == 2:
        lang = pycountry.languages.get(alpha_2=lang_input)
        if lang:
            return lang.alpha_2.upper()

    if len(lang_input) == 3:
        lang = pycountry.languages.get(alpha_3=lang_input)
        if lang and hasattr(lang, 'alpha_2'):
            return lang.alpha_2.upper()

    lang = pycountry.languages.get(name=lang_input.capitalize())
    if lang and hasattr(lang, 'alpha_2'):
        return lang.alpha_2.upper()

    for lang in pycountry.languages:
        if lang_input == lang.name.lower():
            if hasattr(lang, 'alpha_2'):
                return lang.alpha_2.upper()

    return "unknown"

def get_first_audio_language_code(file_path):
    try:
        probe = ffmpeg.probe(
            file_path,
            v='error',
            select_streams='a:0',
            show_entries='stream_tags=language',
            of='json'
        )
        tags = probe['streams'][0].get('tags', {})
        lang_tag = tags.get('language', None)
        if lang_tag:
            return get_language_code_2(lang_tag)
        else:
            return "unknown"
    except Exception as e:
        print(f"Error reading audio language for {file_path}: {e}")
        return "unknown"

def get_audio_channel_description(file_path):
    try:
        probe = ffmpeg.probe(
            file_path,
            v='error',
            select_streams='a:0',
            show_entries='stream=channels',
            of='json'
        )
        channels = probe['streams'][0].get('channels', 0)

        if channels == 1:
            return "Single Audio"
        elif channels == 2:
            return "Dual Audio"
        elif channels > 2:
            return "Multi Audio"
        else:
            return "unknown"
    except Exception as e:
        print(f"Error reading audio channels for {file_path}: {e}")
        return "unknown"