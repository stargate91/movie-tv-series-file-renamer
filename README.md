# 🎬 Movie & TV Series File Renamer (Python CLI Tool)

A Python-based CLI tool that automatically renames your movie and TV series files using metadata fetched from **TMDb** and **OMDb** APIs.

This tool is ideal for organizing your video library with clean, structured filenames based on customizable templates. It supports both automatic and interactive modes and has undo capabilities and dry-run safety.

---

## 🚀 Features

- 🔍 **Automatic Metadata Lookup** (via TMDb & OMDb)
- 🎯 **Highly Configurable Renaming Templates**
- 🧠 **Guess Metadata from Filename and/or Folder Name**
- 💬 **Interactive Mode for Manual Selection**
- 🛠️ **Batch Mode (No Prompts / Fully Automated)**
- 🧪 **Dry Run Mode (Safe Preview)**
- 📁 **Recursive Folder Search**
- ⏪ **Undo Last Rename Operation**
- 🧹 **Sample File Detection (under development)**
- 📝 **Configurable Minimum Video Size**
- 🧾 **Logging with Timestamps**
- 🧑‍💻 **Custom Variable Support in Templates**
- 🐍 **Pure Python, No External Dependencies Except ffmpeg & APIs**

---

## 🧰 Planned Features

- 🌍 Language Preference for Metadata (e.g., English, Hungarian)
- 📜 Subtitle and Audio Track File Handling
- 📂 Folder Renaming / Moving Support (e.g., `Movies/Title (Year)/`)
- ❓ Partial / Missing Episode Info Handling
- 🖱️ Simple GUI (drag & drop + config editor)

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/movie-tv-renamer.git
cd movie-tv-renamer
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup `.env` File for API Keys

Create a `.env` file in the `data/` folder with the following:

```env
TMDB_API_KEY=your_tmdb_key_here
TMDB_BEARER_TOKEN=your_tmdb_token_here
OMDB_API_KEY=your_omdb_key_here
```

---

## ⚙️ Configuration (`config.ini`)

You can customize almost everything in `config.ini`, located in the project root.

### Example:

```ini
[GENERAL]
folder_path = E:\dl_torrent
interactive = True
skipped = False
undo = True
history_file = \rename_history\rename_history_2025-07-25_1310.json
vid_size = 500
recursive = True
source_mode = fallback
live_run = False
sample = False
sample_keywords = sample,minta,trailer
use_emojis = True

[TEMPLATES]
custom_variable = Collection1
movie_template = {custom_variable} + {movie_title} {movie_year}-{resolution}
episode_template = {custom_variable} + {series_title} - S{season_number}E{episode_number} - {episode_title}-{air_date}-{resolution}
zero_padding = True
filename_case = title
separator = space

[API]
omdb_key = your_omdb_key_here
tmdb_key = your_tmdb_key_here
tmdb_bearer_token = your_tmdb_token_here
```

---

## 🧪 Running the Tool

### Dry Run (Preview Mode)

```bash
python main.py
```

### Live Run (Actually Renames Files)

```bash
python main.py --live
```

### Undo Last Rename

```bash
python main.py --undo
```

### Skip Config File and Use CLI Args Only

```bash
python main.py --folder "E:\dl\anime" --interactive --recursive
```

---

## 📁 Project Structure

```
📦movie-tv-renamer
├── main.py                  # Entry point
├── config.py                # Loads CLI args + config.ini
├── config.ini               # Custom settings
├── collector.py            # Gathers video files
├── parser.py               # Parses filename/folder metadata
├── api_client.py           # Fetches data from TMDb and OMDb
├── metadata.py             # Primary metadata handler
├── metadata_enricher.py    # Adds extra metadata (e.g., ratings)
├── metadata_standardizer.py# Normalizes all metadata
├── result_manager.py       # Sorts result into match types
├── movie_handlers.py       # Handles movie-specific logic
├── series_id_handlers.py   # Handles episode/series logic
├── renamer.py              # Renaming logic
├── undo.py                 # Undo functionality
├── logger_setup.py         # Logging config
├── video_metadata.py       # FFmpeg-based technical info
├── sample.py               # Sample file detection (in progress)
├── ui_ux.py                # CLI printing and input
├── cache.py                # Optional caching
├── build.py                # Utility functions for build
├── data/                   # Stores .env, temp cache
├── logs/                   # Logs with timestamps
├── rename_history/         # Stores rename history for undo
├── tests/                  # Tests (in progress)
└── requirements.txt
```

---

## 🎞 Supported Video Formats (Scalable)

- `.mp4`
- `.mkv`
- `.avi`
- `.mov`
- `.wmv`
- `.mpeg`
- `.mpg`

---

## 🧪 Sample Detection (In Progress)

The tool can detect sample/trailer files based on:
- Keywords (`sample`, `trailer`, etc.)
- File size (under threshold)

Planned actions:
- Rename
- Move to subfolder
- Delete

---

## 💡 Tips

- Always start with **dry run mode** to avoid accidental renames.
- Use the **interactive mode** to manually select titles when unsure.
- Check logs for detailed info on what happened.

---

## 🧠 Technologies Used

- `Python 3.9+`
- `requests`, `ffmpeg-python`, `guessit`
- `dotenv` for API credentials
- `ffmpeg` (must be installed separately!)

---

## 📋 License

This project is open-source and free to use. Contributions, bug reports, and feature requests are very welcome!

---

## 📧 Contact

Made by a Python enthusiast learning through building useful tools.  
If you have feedback or suggestions, feel free to open an issue or fork the repo!
