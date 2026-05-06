# RENDA - Smart Media Organizer

Hi, this is a python project I made to rename and organize my movies and TV shows. I had a lot of messy folders and I wanted to learn PySide6, so I built this.

## What it does

Basically, it scans your folders and looks for video files. Then it tries to guess what movie or TV show it is, and uses the TMDB API to get the correct titles, seasons, and episodes. 

- It can sort files into separate folders for movies and TV shows.
- It finds "extras" like trailers or subtitles and keeps them with the main video.
- You can create your own naming templates using variables like {Title} or {Resolution}.
- If it guesses wrong, you can use the Manual Resolve window to search TMDB yourself.
- It saves everything into a local sqlite database so it's faster the second time.

## How to install

I made a requirements file, so you can just install the packages. I use python 3.11 but it probably works on newer versions too.

1. Clone or download this code.
2. Open terminal and run: pip install -r requirements.txt
3. Run python main.py to start the app.

Note: You will need to go into the Settings tab inside the app to put your TMDB and OMDB api keys. It won't download metadata without them!

## Structure

I tried to organize the code so it's not all in one file. 
- main.py is the entry point.
- core/ has the backend logic, like the database code and the file scanner.
- ui/v3/ has all the PySide6 widgets and views. I rewrote the UI a few times, so this is version 3.
- api/ is where the requests to TMDB and OMDB happen.

## Things I want to fix later

- Sometimes the regex for finding season numbers fails if the file is named really weirdly.
- I want to add more tests because sometimes I break things when I change the UI.
- Make the scanning even faster.

Thanks for checking out my code.
