# Media File Renamer

This is a program I made to rename movie and TV show files. It uses PySide6 for the interface and gets data from TMDb and OMDb APIs.

## What it does
- You can drag and drop folders or files into the window.
- It scans the files and tries to find out what movie or show they are.
- It shows a list of files with their current names and the new names.
- If it's not sure, you can manually select the correct movie or show from a list.
- It supports batch renaming for multiple files at once.
- There is a settings menu to put your API keys and change how the files are named.

## How to use it
1. Install the requirements using pip.
2. Get your API keys from TMDb and OMDb.
3. Run main.py.
4. Select a folder or drag files in.
5. Click "Download Metadata" to get the information.
6. Check if the names are correct and then rename them.

## Requirements
- Python 3.x
- PySide6
- requests
- python-dotenv
- guessit
- ffmpeg (for some metadata)

## Project Structure
- main.py: This is where the program starts.
- ui/: Contains all the code for the windows and buttons.
- core/: Contains the main logic and settings management.
- metadata/: Code for finding files and handling information.
- utils/: Helper scripts like the API client.
- data/: Where the .env file with API keys goes.

## Installation
First, clone the project. Then install everything:
```bash
pip install -r requirements.txt
```
Make sure you have a .env file in the data folder with these:
- TMDB_API_KEY
- OMDB_API_KEY
- TMDB_BEARER_TOKEN

## To Do
- Better error handling for when the internet is down.
- Add support for more video formats.
- Make the undo function work better.
