import os
import ffmpeg

def check_if_video_file(file_path, min_size_bytes):
    file_extension = os.path.splitext(file_path)[1].lower()
    valid_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.mpeg', '.mpg']

    if file_extension in valid_extensions:
        file_size = os.path.getsize(file_path)
        return file_size >= min_size_bytes
    return False

def get_video_files_from_directory(directory, min_size_bytes):
    video_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and check_if_video_file(file_path, min_size_bytes):
            video_files.append(file_path)

    video_files = sorted(video_files)
    
    return video_files

def get_video_files(root_folder, recursive):
    min_size_mb = 500
    min_size_bytes = min_size_mb * 1024 * 1024

    video_files = []

    if recursive:
        for root, dirs, files in os.walk(root_folder):
            video_files.extend(get_video_files_from_directory(root, min_size_bytes))
    else:
        video_files.extend(get_video_files_from_directory(root_folder, min_size_bytes))

    return video_files

def get_resolution_from_file(file_path):
    try:
        probe = ffmpeg.probe(file_path, v='error', select_streams='v:0', show_entries='stream=width,height')
        width = probe['streams'][0]['width']
        height = probe['streams'][0]['height']
        
        if width >= 1920:
            return 1080
        elif width >= 1280:
            return 720
        else:
            return 480
    except ffmpeg._run.Error as e:
        print(f"Error getting resolution for {file_path}: {e}")
        return "Unknown"


def rename_files(api_results, dry_run):
    renamed_files = []

    for file_data in api_results: 
        file_path = file_data['file_path']
        metadata = file_data['data']

        if 'Title' in metadata:
            title = metadata['Title']
            year = metadata['Year']
        elif 'title'in metadata:
            title = metadata['title']
            release_date = metadata['release_date']
            year = release_date.split('-')[0]
        elif 'results' in metadata:
            title = metadata['results'][0]['title']
            release_date = metadata['results'][0]['release_date']
            year = release_date.split('-')[0]
        else:
            print("[ERROR] Missing title or year from API response.")
            continue


        resolution = get_resolution_from_file(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        new_filename = f"{title} - {year}_{resolution}p{file_extension}"
        directory = os.path.dirname(file_path)
        new_file_path = os.path.join(directory, new_filename)

        print(f"Old name: {file_path} -> New name: {new_filename}")

        if not dry_run:
            os.rename(file_path, new_file_path)
            renamed_files.append(new_file_path)

    return renamed_files

def handle_multiple_movie_results(multiple_results):
    handled_files = []
    for file_data in multiple_results:
        print(f"\nMultiple movie results found for: {file_data['file_path']}")
        results = file_data['data']['results']
        
        for idx, result in enumerate(results, start=1):
            title = result.get("title")
            release_date = result.get("release_date")
            print(f"{idx}. {title} ({release_date})")

        try:
            choice = int(input(f"Please select a movie by number (1-{len(results)}): "))
            if 1 <= choice <= len(results):
                selected_result = results[choice - 1]
                selected_title = selected_result.get('title')
                selected_release_date = selected_result.get("release_date")
                print(f"User selected: {selected_title} ({selected_release_date})")
                
                handled_files.append({
                    "file_path": file_data['file_path'],
                    "data": {
                        "title": selected_title,
                        "release_date": selected_release_date
                    }
                })
            else:
                print("Invalid choice. No movie selected.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    

    return handled_files


def handle_no_results(no_results, api_client, api_source):
    handled_files = []

    for file_data in no_results:

        print(f"\nAttempting manual search for: {file_data['file_path']}")

        manual_search = input(f"\nWould you like to search manually? (y/n): ").strip().lower()

        if manual_search == 'y':
            search_title = input("Enter movie title: ").strip()
            search_year = input("Enter movie release year (or leave empty to skip): ").strip()

            if not search_year:
                search_year = None

            if api_source == "omdb":
                data = api_client.get_from_omdb(search_title, search_year)
            elif api_source == "tmdb":
                data = api_client.get_from_tmdb_movie(search_title, search_year)
            else:
                print("[ERROR] Unsupported API source for manual search.")
                continue
            
            if data:
                if api_source == "omdb":
                    if data.get("Response") == "True":
                        print(f"Found result: {data['Title']} ({data['Year']})")
                        handled_files.append({
                            "file_path": file_data['file_path'],
                            "data": {
                                "Title": data['Title'],
                                "Year": data['Year']
                            }
                        })
                    else:
                        print(f"No manual results found for {search_title}.")
                elif api_source == "tmdb":
                    if data.get("total_results") > 0:
                        results = data['results']
                        print("Found results:")
                        for idx, result in enumerate(results, start=1):
                            print(f"{idx}. {result['title']} ({result['release_date']})")

                        try:
                            choice = int(input(f"Please select a movie by number (1-{len(results)}): "))
                            if 1 <= choice <= len(results):
                                selected_result = results[choice - 1]
                                selected_title = selected_result.get('title')
                                selected_release_date = selected_result.get('release_date')
                                print(f"User selected: {selected_title} ({selected_release_date})")
                                
                                handled_files.append({
                                    "file_path": file_data['file_path'],
                                    "data": {
                                        "title": selected_title,
                                        "release_date": selected_release_date
                                    }
                                })
                            else:
                                print("Invalid choice. No movie selected.")
                        except ValueError:
                            print("Invalid input. Please enter a number.")
                    else:
                        print(f"No manual results found for {search_title}.")
        else:
            print(f"Skipping manual search for {file_data['file_path']}.")

    return handled_files

def handling_series(api_results):

    for file_data in api_results:
        for key, value in file_data.items():
            print(f"Key: {key}, Value: {value}")
