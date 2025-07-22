DEFAULT_CONFIG = """
[GENERAL]
folder_path = E:\\dl_torrent
# Path to the folder containing the video files to rename.
# Example: "E:\\dl_torrent" or "/home/user/videos"
# Use double backslashes \\ on Windows or forward slashes /

vid_size = 500
# Minimum video file size (in megabytes) to include in processing.
# Helps exclude sample clips or other small, irrelevant video files.

recursive = True
# Whether to search subdirectories recursively for video files.
# Possible values: True or False

source = tmdb
# API source for metadata lookup.
# Options: "omdb", "tmdb"
# OMDb only gives one result if there is one and only useable for movies.
# TMDb handles both movies and series, in case you choose "omdb" here, for episode files still the API source is TMDb.

live_run = False
# If True, the program will actually rename files.
# If False, it's a dry run that only prints changes.

use_emojis = False
# Whether to display emojis in terminal messages for better readability.
# Set to True to enable emojis, or False to keep output plain and compatible with all terminals.
# 
# Emojis usually work well in:
#   - Modern terminals (Windows Terminal, macOS Terminal, Linux with UTF-8 support)
#   - IDE-integrated terminals (e.g. VSCode, PyCharm)
#
# Emojis may not display correctly in:
#   - Legacy Windows CMD or PowerShell without Unicode font support
#   - Non-UTF-8 terminals or basic remote shells (e.g. some SSH clients)
#
# For maximum compatibility (e.g. when running scripts on remote servers), keep this set to False.

[TEMPLATES]

# Note:
# If a variable cannot be extracted from the source (API, filename, or folder name),
# or the data does not exist, the value will be replaced with "unknown".

movie_template = {movie_title} {movie_year}-{resolution}
# Template for renaming movie files.
# Available variables:
#   movie_title                  - Movie title
#   movie_release_date           - Full release date (e.g. 2022-03-15)
#   movie_year                   - Release year (e.g. 2022)
#   resolution                   - Video resolution (e.g. 1080p, 4K)
#   video_codec                  - Video codec (e.g. H.264, H.265)
#   video_bitrate                - Video bitrate (e.g. 5 mbps)
#   framerate                    - Framerate (e.g. 23.98 fps, 25 fps)
#   audio_codec                  - Audio codec of the first audio track (e.g. Dolby Digital, DTS)
#   audio_channels               - Number of audio channels of the first audio track (e.g. Stereo, 5.1)
#   first_audio_channel_language - Language of the first audio track (e.g. en, hu)
#   audio_channels_description   - Human-readable audio description (e.g. Single Audio, Dual Audio, Multi Audio)

# Example:
#   "Inception 2010-1080p H.264 AAC Stereo"

episode_template = {series_title} - S{season}E{episode} - {episode_title}-{air_date}-{resolution}
# Template for renaming episode files.
# Available variables:
#   series_title                  - Name of the TV series
#   first_air_date                - Series first air date (e.g. 2010-04-17)
#   first_air_year                - Year of the first air date (e.g. 2010)
#   last_air_date                 - Series last air date (e.g. 2024-12-01)
#   last_air_year                 - Year of the last air date (e.g. 2024)
#   status                        - Current status of the series (e.g. Returning Series, Ended)
#   episode_title                 - Title of the episode
#   season                        - Season number (with zero padding, next setting, e.g. 01, 02)
#   episode                       - Episode number (with zero padding, next setting, e.g. 03, 10)
#   air_date                      - Episode air date (e.g. 2023-03-05)
#   air_year                      - Year of the air date (e.g. 2023)
#   resolution                    - Video resolution (e.g. 1080p, 4K)
#   video_codec                   - Video codec (e.g. H.264, H.265)
#   video_bitrate                 - Video bitrate (e.g. 5 mbps)
#   framerate                     - Framerate (e.g. 23.98 fps, 25 fps)
#   audio_codec                   - Audio codec of the first audio track (e.g. Dolby Digital, DTS)
#   audio_channels                - Number of audio channels of the first audio track (e.g. Stereo, 5.1)
#   first_audio_channel_language  - Language of the first audio track (e.g. en, hu)
#   audio_channels_description    - Human-readable audio description (e.g. Single Audio, Dual Audio, Multi Audio)

# Example:
#   "Friends - S01E03 - The One with the Thumb-1994-09-22-720p"

zero_padding = True
# Whether to use zero-padding for season and episode numbers.
# True -> S01E01
# False -> S1E1

[API]
omdb_key = your_omdb_key_here
# Your API key for OMDb.
# Required if you use "omdb" as the source
# Only for movies and you can get only 1 result / movie

tmdb_key = your_tmdb_key_here
# Your API key for TMDb.
# Required if you use "tmdb" as the source.

tmdb_bearer_token = your_tmdb_token_here
# Bearer token for TMDb API authorization.
# Required if you use "tmdb" as the source.
"""

KEYS_ERROR_MESSAGE = """
This tool needs valid API credentials for OMDb and TMDb to work properly.

You can provide them in one of the following ways:

1. In the config.ini file (created automatically next to the executable):

[API]
omdb_key = your_omdb_key
tmdb_key = your_tmdb_api_key
tmdb_bearer_token = your_tmdb_bearer_token

2. Or via a .env file in the 'data/' folder:

OMDB_KEY=your_omdb_key
TMDB_KEY=your_tmdb_api_key
TMDB_BEARER_TOKEN=your_tmdb_bearer_token

Without these keys, the program cannot fetch movie or series metadata.
"""