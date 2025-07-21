# 🎬 Movie / TV Series Renamer

This is a Python-based tool that automatically renames your movie and TV series video files using metadata from OMDb or TMDb APIs.\
It's built to help organize downloaded video content by giving meaningful and standardized file names.

## ✅ Features

- Automatically renames **movie** and **episode** files using API metadata
- Supports both **OMDb** (movies only) and **TMDb** (movies and series)
- If multiple results are found, you can manually choose the correct one
- If no match is found, you can perform a manual API search
- Falls back from file name to folder name when needed
- Fully customizable file name templates
- Supports **dry-run** mode (preview renaming without changing anything)
- Command-line arguments to override config settings
- Environment variable or `.ini` based configuration
- Automatically ignores small video samples (default < 500 MB)
- Future plans include subtitle handling, logging, batch mode, and more!

---

## 📁 Folder Structure

```
Movie-TV-Renamer/
│
├── api_client.py               # Handles API communication
├── cache.py                    # Handles result caching
├── config.ini                  # Main config file (user-editable)
├── config.py                   # Loads CLI args, .env and config.ini
├── file_ops.py                 # File/folder renaming logic
├── main.py                     # Entry point
├── meta.py                     # Metadata parsing and extraction
├── meta_from_files.py          # Getting tech metadata from the video files (e.g resolution, video codec)
├── movie_handler.py            # Handles movie-specific logic
├── series_handler_id.py        # TMDb ID-based series handling
├── series_handler_episode.py   # Episode-level TMDb handling
├── outputs.py                  # Printing and formatting outputs
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .gitignore
└── data/
    └── .env                    # (Optional) API keys can be stored here
```

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourname/movie-tv-renamer.git
cd movie-tv-renamer
```

### 2. Install requirements

It's recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

---

## 🔐 API Keys

You need at least one API key to use this tool.

1. **OMDb API Key** (Movies only): [https://www.omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx)
2. **TMDb API Key + Bearer Token** (Movies & TV): [https://developer.themoviedb.org/](https://developer.themoviedb.org/)

You can set them in two ways:

### Option 1: `.env` file (recommended)

Create a file called `.env` inside the `data/` folder:

```
OMDB_KEY=your_omdb_key_here
TMDB_KEY=your_tmdb_key_here
TMDB_BEARER_TOKEN=your_tmdb_bearer_token_here
```

### Option 2: Edit `config.ini` under `[API]` section

---

## 🧪 Configurations

All default settings are stored in `config.ini`. Here's what you can configure:

### `[GENERAL]`

- `folder_path` – The base directory to scan for files
- `recursive` – Search subdirectories too (`True` / `False`)
- `source` – `"tmdb"` or `"omdb"`
- `live_run` – If `True`, it renames files. If `False`, it's a dry-run

### `[TEMPLATES]`

Customize the naming format using these variables.

#### Movie Example:

```ini
movie_template = {movie_title} {movie_year}-{resolution}
```

#### Episode Example:

```ini
episode_template = {series_title} - S{season}E{episode} - {episode_title}-{air_date}-{resolution}
```

**Variables supported include:**

- `movie_title`, `movie_year`, `resolution`, `video_codec`, `audio_channels`, etc.
- `series_title`, `season`, `episode`, `episode_title`, `air_date`, and more

### `[API]`

Put your keys here if you're not using `.env`.

---

## 🚀 How to Run

### Basic usage (from `config.ini`):

```bash
python main.py
```

### With command-line arguments:

```bash
python main.py --folder "E:\Movies" --live-run --source tmdb
```

### Useful CLI options:

- `--folder`: Specify a folder directly
- `--recursive`: Search inside subfolders
- `--live-run`: Actually rename files (without it, just shows changes)
- `--movie_template` / `--episode_template`: Override templates
- `--zero-padding`: Use zero-padding like `S01E01`

---

## 🧠 How It Works

1. Tries to extract the movie/episode title from the **file name**
2. Searches API for matches
   - If **one match**, it uses that
   - If **multiple or none**, tries using the **folder name**
3. If still not resolved, lets the user search manually
4. Renames the file based on the chosen template
5. If `live_run` is `False`, it just prints what would happen

---

## 🧰 Requirements

- Python 3.7+
- Dependencies (in `requirements.txt`)
  - `requests`
  - `python-dotenv`
  - `ffmpeg-python`
  - `guessit`
  - `pycountry`

---

## 🚣️ Planned Features

- Rename folders too (not just files)
- Rename/move subtitle and audio track files
- Skip or delete sample files automatically
- Logging (to console and file)
- "Undo last rename" functionality
- Handle skipped files later
- Batch mode (no interaction)
- Custom user-defined template variables
- API localization (e.g. support for Hungarian titles)
- GUI (possibly in the future)

---

## ⚠️ Notes

- Minimum video size is currently **500 MB** (hardcoded)
- Only TMDb is used for **TV series**
- OMDb only works for **movies**
- If no renaming template variables are found (like last_air_date because the series isn't ended yet), the value becomes `"unknown"`
- Files are **not renamed** unless `--live-run` or `live_run=True` is set!

---

## 📬 Contact

For questions or ideas, feel free to open an issue or fork and contribute!

---

**Enjoy your clean and organized video library! 🎉**

