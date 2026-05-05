"""
Centralized constants for the Movie Renamer engine.
"""

RESOLUTION_MAP = {
    2160: "4K",
    1080: "1080p",
    720: "720p",
    480: "480p",
    576: "576p"
}

VIDEO_CODEC_MAP = {
    "H264": "x264",
    "AVC": "x264",
    "HEVC": "x265",
    "H265": "x265",
    "AV1": "AV1",
    "VP9": "VP9",
    "MPEG4": "XviD"
}

AUDIO_CODEC_MAP = {
    "AC-3": "AC3",
    "E-AC-3": "EAC3",
    "DCA": "DTS",
    "TRUEHD": "TrueHD",
    "FLAC": "FLAC",
    "AAC": "AAC",
    "MP3": "MP3"
}

AUDIO_CHANNELS_MAP = {
    "1": "1.0",
    "2": "2.0",
    "stereo": "2.0",
    "6": "5.1",
    "5.1(side)": "5.1",
    "8": "7.1",
    "7.1(wide)": "7.1"
}
