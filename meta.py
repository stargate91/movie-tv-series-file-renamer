import re
import os

def series_s_e_format(parts):
    for part in parts:
        if "s" in part and "e" in part:
            try:
                season_episode = part.split("e")
                if len(season_episode) == 2:
                    season = int(season_episode[0].replace("s", ""))
                    episode = int(season_episode[1])
                    title = " ".join(parts[:parts.index(part)]).strip().title()
                    return title, season, episode
            except ValueError:
                None

def series_x_format(parts):
    for part in parts:
        if "x" in part:
            try:
                season_episode = part.split("x")
                if len(season_episode) == 2:
                    season = int(season_episode[0])
                    episode = int(season_episode[1])
                    title = " ".join(parts[:parts.index(part)]).strip().title()
                    return title, season, episode
            except ValueError:
                return None

def parse_series(filename):
    filename = filename.lower()

    parts_by_dots = filename.replace("-"," ").replace(" ", "").split(".")
    parts_by_spaces = filename.replace("-"," ").split(" ")

    result = series_s_e_format(parts_by_dots)

    if result:
        return result
    else:
        result = series_s_e_format(parts_by_spaces)
        if result:
            return result
        else:
            result = series_x_format(parts_by_dots)
            if result:
                return result
            else:
                result = series_x_format(parts_by_spaces)
                if result:
                    return result
                else:
                    return "Unknown Title", "Unknown", "Unknown"

def remove_resolution_from_title(title):
    title = re.sub(r"\b(?:720|1080|1440|2160)p\b", "", title)
    title = re.sub(r"\b(?:HD|SD|BluRay|HDRip|WEBRip|WEB-DL|HDTV|CAM|DVDRip)\b", "", title)
    return title.strip()

def extract_metadata_from_filename(filename, file_type):
    
    if file_type == "series":
        title, season, episode = parse_series(filename)
        if title != "Unknwon Title" and season != "Unknown" and episode != "Unknown":
            return {"title": title, "season": season, "episode": episode, "year": "Unknown Year"}
        else:
            return {"title": filename.strip().replace('.', ' '), "season": "Unknown", "episode": "Unknown", "year": "Unknown Year"}

    else:
        filename = remove_resolution_from_title(filename)
        match = re.match(r"(.*?)(\d{4})", filename.strip())
        if match:
            title = match.group(1).strip().replace(' ', '.')
            year = match.group(2).strip()
            return {"title": title, "year": year}
        else:
            return {"title": filename.strip().replace('.', ' '), "year": "Unknown Year"}

def extract_metadata_from_folder(folder_name, file_type):
    folder_name = remove_resolution_from_title(folder_name)

    if file_type == "series":
        match = re.match(r"([^\d]+?)\s*S(\d{1,2})E(\d{1,2})\s*(\d{4})", folder_name.strip().replace('.', ' '))
        if match:
            title = match.group(1).strip().replace(' ', '.')
            season = match.group(2).strip()
            episode = match.group(3).strip()
            year = match.group(4).strip()
            return {"title": title, "season": season, "episode": episode, "year": year}
        else:
            return {"title": folder_name.strip().replace('.', ' '), "season": "Unknown", "episode": "Unknown", "year": "Unknown Year"}

    else:
        match = re.match(r"(.*?)(\d{4})", folder_name.replace('.', ' '))
        if match:
            title = match.group(1).strip().replace(' ', '.')
            year = match.group(2).strip()
            return {"title": title, "year": year}
        else:
            return {"title": folder_name.strip().replace('.', ' '), "year": "Unknown Year"}

def clean_title(title):
    title = title.replace('.', ' ')
    title = title.replace(',', ' ')
    return title.strip()

def process_video_files(video_files, meta, file_type):
    processed_files = []

    for file in video_files:
        file_name = os.path.basename(file)
        folder_name = os.path.basename(os.path.dirname(file))

        metadata = {"title": "Unknown Title", "year": "Unknown Year"}

        if meta == "folder":
            metadata = extract_metadata_from_folder(folder_name, file_type)
        else:
            metadata = extract_metadata_from_filename(file_name, file_type)

        metadata['title'] = clean_title(metadata['title'])

        if 'year' not in metadata or metadata['year'] == "":
            metadata['year'] = "Unknown Year"

        if file_type == "series":
            if "season" not in metadata:
                metadata["season"] = "Unknown"
            if "episode" not in metadata:
                metadata["episode"] = "Unknown"

        processed_files.append({"file_path": file, "metadata": metadata})

    return processed_files

def transfer_metadata_to_api(processed_files, api_client, api_source, file_type):

    no_results = []
    one_result = []
    multiple_results = []

    for file_data in processed_files:
        metadata = file_data.get('metadata', {})
        title = metadata.get('title')
        year = metadata.get('year', 'Unknown Year')
        season = metadata.get('season')
        episode = metadata.get('episode')

        if 'season' not in metadata or 'episode' not in metadata:
            print(f"[WARNING] Missing 'season' or 'episode' in metadata for {file_data['file_path']}")
        
        if title and year:
            if api_source == "omdb" and file_type == "movie":
                data = api_client.get_from_omdb(title, year)
            elif api_source == "tmdb" and file_type == "movie":
                data = api_client.get_from_tmdb_movie(title, year)
            elif file_type == "series":
                data = api_client.get_from_tmdb_tv(title, year)
            else:
                print("[ERROR] Incorrect arguments for API source or content type.")
                data = None
        else:
            print("[ERROR] Missing title or year in metadata.")
            data = None

        if file_type == "series" and data:
            if data.get("total_results") == 0:
                print(f"No results found for {file_data['file_path']}: No results in TMDB response.")
                no_results.append({"file_path": file_data['file_path'], "season": season, "episode": episode})
            elif data.get("total_results") == 1:
                one_result.append({"file_path": file_data['file_path'], "season": season, "episode": episode, "data": data})
                print(f"One result found for {file_data['file_path']}: {data}")
            elif data.get("total_results") > 1:
                multiple_results.append({"file_path": file_data['file_path'], "season": season, "episode": episode, "data": data})
                print(f"Multiple results found for {file_data['file_path']}: {data}")
            else:
                print(f"No data found for {file_data['file_path']}.")
                no_results.append(file_data)         

        if file_type == "movie" and data:
            if api_source == "omdb":
                if data.get("Response") == "False":
                    print(f"No results found for {file_data['file_path']}: {data['Error']}")
                    no_results.append(file_data)
                elif data.get("Response") == "True":
                    one_result.append({"file_path": file_data['file_path'], "data": data})
                    print(f"One result found for {file_data['file_path']}: {data}")
            elif api_source == "tmdb":
                if data.get("total_results") == 0:
                    print(f"No results found for {file_data['file_path']}: No results in TMDB response.")
                    no_results.append(file_data)
                elif data.get("total_results") == 1:
                    one_result.append({"file_path": file_data['file_path'], "data": data})
                    print(f"One result found for {file_data['file_path']}: {data}")
                elif data.get("total_results") > 1:
                    multiple_results.append({"file_path": file_data['file_path'], "data": data})
                    print(f"Multiple results found for {file_data['file_path']}: {data}")

    return no_results, one_result, multiple_results
