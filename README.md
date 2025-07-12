
# Movie/TV Series Renamer

A simple Python script that automatically renames your movie and TV series video files based on metadata (like title, year, resolution, etc.) pulled from APIs such as OMDb and TMDb. It also allows you to manually choose the correct result when there are multiple matches or search for a result when no match is found.

---

## Features

- **Auto-Rename**: The script will automatically rename your video files using metadata from OMDb or TMDb.
- **Manual Selection**: If there are multiple results found, you can manually select the correct one or search for a result.
- **Metadata Sources**: Choose between OMDb (default) or TMDb for metadata search.
- **Folder and File Metadata**: The script can extract metadata from the filename or the folder name, depending on your preference.
- **Recursive Search**: Option to recursively process files in subdirectories.

---

## Installation

### Prerequisites

1. Python 3.6+
2. You will need **OMDb** and **TMDb** API keys. You can sign up for these APIs:
   - OMDb: [https://www.omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx)
   - TMDb: [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)

### Step 1: Clone this repo

```bash
git clone https://github.com/your-username/movie-tv-series-renamer.git
cd movie-tv-series-renamer
```

### Step 2: Install dependencies

Create a virtual environment (optional but recommended):

```bash
python3 -m venv venv
source venv/bin/activate   # On Windows, use `venv\Scriptsctivate`
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Step 3: Set up environment variables

Create a `.env` file in the project root and add your API keys:

```plaintext
OMDB_KEY=your_omdb_api_key
TMDB_KEY=your_tmdb_api_key
TMDB_BEARER_TOKEN=your_tmdb_bearer_token
```

---

## Usage

Run the script with your folder of video files:

```bash
python main.py /path/to/your/videos --recursive --meta "file" --source "omdb" --type "movie"
```

### Available Options

- `folder`: Path to the folder containing video files to rename.
- `--recursive`: Whether to include video files in subdirectories. By default, it only processes the files in the specified folder.
- `--meta`: The metadata source to prioritize. Can be either `file` or `folder`. Default is `file`.
- `--source`: Which API to use for metadata search. Options are `omdb` or `tmdb`. Default is `omdb`.
- `--type`: Type of content. Choose either `movie` or `series`. Default is `movie`.
- `--second`: Use a second metadata search source (opposite of the one set in `--meta`).

---

## Future Plans

- **Resolution and Quality Update**: Automatically update the file names with the correct resolution and quality information pulled from metadata (e.g., `1080p`, `BluRay`).
- **Multiple File Format Support**: Expand the supported file formats for video files and handle potential edge cases.
- **Batch Renaming**: Implement a feature for bulk renaming files from multiple folders at once.
- **Enhanced Metadata**: Include additional metadata like actors, directors, genres, and IMDb ratings in the renamed files.
- **Cloud Integration**: Add an option to automatically upload renamed files to cloud storage services like Google Drive or Dropbox.
- **AI-powered Matching**: Add AI-based improvements to detect and correct file name inconsistencies, such as misspellings or format errors.
- **Error Logging and Reporting**: Implement a better logging system to track all renaming actions, errors, and warnings, to help debug any issues in the renaming process.

---

## Contributing

If you'd like to contribute, feel free to fork the repository, create a branch, and submit a pull request! Please make sure to write tests for any new functionality you add.

---

## License

This project is open-source and available under the [MIT License](LICENSE).
