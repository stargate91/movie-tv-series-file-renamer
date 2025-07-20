import os

def normalize_season_episode(file_data):
    season = file_data.get('season_file') or file_data.get('season_folder') or 'unknown'
    episode = file_data.get('episode_file') or file_data.get('episode_folder') or 'unknown'

    if season == 'unknown':
        print(f"[WARNING] Missing season number for file data: {file_data}")
    if episode == 'unknown':
        print(f"[WARNING] Missing episode number for file data: {file_data}")

    return season, episode

def normalize_episodes(episodes, api_client):
    print("\n=== NORMALIZE EPISODES METADATA ===\n")

    handled_files = []
    unexpected_files = []

    for file_data in episodes:
        data = file_data['details']
        season_details = data['results'][0]
        series_id = season_details['id']
        season_details.update({'first_air_year': season_details['first_air_date'].split('-')[0]})
        season_details['title'] = season_details.pop('name')

        season, episode = normalize_season_episode(file_data)

        season_data = api_client.get_from_tmdb_tv_detail(series_id)
        if season_data.get('status') == "Ended":
            last_air_date = season_data.get('last_air_date')
            if last_air_date:
                season_details.update({
                    'last_air_date': last_air_date,
                    'last_air_year': last_air_date.split('-')[0]
                })
            else:
                season_details.update({
                    'last_air_date': 'unknown',
                    'last_air_year': 'unknown'
                })
        else:
            season_details.update({
                'status': season_data.get('status', 'unknown')
            })

        if 'unknown' in [season, episode]:
            print(f"[WARNING] Unexpected files for {file_data['file_path']}. Manual renaming needed.")
            unexpected_files.append(file_data)
        else:
            handled_files.append({
                'file_path': file_data['file_path'],
                'file_type': file_data['file_type'],
                'extras': file_data['extras'],
                'season': season,
                'episode': episode,
                'season_details': season_details
            })
            print("Normalized successfully: {file_data['file_path']}")

    return handled_files, unexpected_files

# ======================================================================
# ======================================================================
# ======================================================================

def group_by_folders(episodes):
    folders = {}
    main_folders = {}

    for file_data in episodes:
        file_path = file_data['file_path']
        directory = os.path.dirname(file_path)
        main_directory = os.path.dirname(directory)

        if directory not in folders:
            folders[directory] = []
        folders[directory].append(file_data)

        if main_directory not in main_folders:
            main_folders[main_directory] = []
            
        if file_data not in main_folders[main_directory]:
            main_folders[main_directory].append(file_data)

    return folders, main_folders

def user_menu(files, folders, main_folders):
    menu_text = (
        "\nChoose how you want to apply the selected metadata for the files above:\n"
        f"  1. Apply to a single file only (e.g: {files[0]['file_path']})\n"
        f"  2. Apply to the entire folder (e.g: {folders})\n"
        f"  3. Apply to the main (parent) folder and all sub‑folders (e.g: {main_folders})\n"
        "  4. Cancel\n"
        "Enter your choice (1–4): "
    )
    while True:
        try:
            raw = input(menu_text).strip()
            if not raw:
                print("Please enter a number between 1 and 4.")
                continue

            choice = int(raw)
            if 1 <= choice <= 4:
                return choice
            else:
                print("Invalid choice. Only 1, 2, 3, or 4 are allowed.")
        except ValueError:
            print("Invalid input. Please type a number (1–4).")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled. Exiting menu.")
            return None

def ask_choice(max_choice):
    try:
        choice = int(input(f"Please select a series by number (1-{max_choice}): "))
        if 1 <= choice <= max_choice:
            return choice
        else:
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

# ======================================================================

def handle_episode_no(episode_no, api_client):
    print("\n=== EPISODES WITH NO SERIES MATCH ===\n")

    if not episode_no:
        print("\n[INFO] There are no episodes with no match. Continue with the next task.")
        return [], []

    for idx, episode in enumerate(episode_no, 1):
        print(f"{idx}. {episode['file_path']}")

    print("\nManual search required for these episodes.\n")

    folders, main_folders = group_by_folders(episode_no) 

    first_folder_key = next(iter(folders))
    first_main_folder_key = next(iter(main_folders))

    action_choice = user_menu(episode_no, first_folder_key, first_main_folder_key)

    skipped_files = []
    handled_files = [] 

    if action_choice == 1:
        for file_data in episode_no:
            file_type = file_data['file_type']
            print(f"Manual series search required for {file_data['file_path']}")
            if input("\nWould you like to search manually? (y/n): ").strip().lower() == 'y':
                search_title = input(f"Enter series title: ").strip()
                search_year = input(f"Enter series release year (or leave empty to skip): ").strip()
                if not search_year:
                    search_year = 'unknown'
                data = api_client.get_from_tmdb_tv(search_title, search_year)
                results = file_data['data']['results']
                print("Found results:")
                for idx, result in enumerate(results, start=1):
                    print(f"{idx}. {result['name']} ({result['first_air_date']})")

                choice = None
                while choice is None:
                    choice = ask_choice(len(results))

                selected_result = results[choice - 1]
                print(f"User selected: {selected_result['name']} ({selected_result['first_air_date']})")
                handled_files.append({
                    "file_path": file_data['file_path'],
                    "file_type": file_data['file_type'],
                    "season": file_data['season'],
                    "episode": file_data['episode'],
                    "details": selected_result,
                    "extras": file_data['extras']
                })
            else:
                return None

    elif action_choice == 2:
        for season_dir, files in folders.items():
            print(f"\nAttempting manual search for: {season_dir}")
            if input("\nWould you like to search manually? (y/n): ").strip().lower() == 'y':
                search_title = input(f"Enter series title: ").strip()
                search_year = input(f"Enter series release year (or leave empty to skip): ").strip()
                if not search_year:
                    search_year = 'unknown'                
                data = api_client.get_from_tmdb_tv(search_title, search_year)
                results = data['results']
                print("Found results:")
                for idx, result in enumerate(results, start=1):
                    print(f"{idx}. {result['name']} ({result['first_air_date']})")

                choice = None
                while choice is None:
                    choice = ask_choice(len(results))

                selected_result = results[choice - 1]
                print(f"User selected: {selected_result['name']} ({selected_result['first_air_date']})")

                for file_data in files:
                    handled_files.append({
                        "file_path": file_data['file_path'],
                        "file_type": file_data['file_type'],
                        "season": file_data['season'],
                        "episode": file_data['episode'],
                        "details": selected_result,
                        "extras": file_data['extras']
                    })
            else:
                return None
    elif action_choice == 3:
        for series_dir, files in main_folders.items():
            print(f"\nAttempting manual search for: {season_dir}")
            if input("\nWould you like to search manually? (y/n): ").strip().lower() == 'y':
                search_title = input(f"Enter series title: ").strip()
                search_year = input(f"Enter series release year (or leave empty to skip): ").strip()
                if not search_year:
                    search_year = 'unknown'
                data = api_client.get_from_tmdb_tv(search_title, search_year)
                results = data['results']
                print("Found results:")
                for idx, result in enumerate(results, start=1):
                    print(f"{idx}. {result['name']} ({result['first_air_date']})")

                choice = None
                while choice is None:
                    choice = ask_choice(len(results))

                selected_result = results[choice - 1]
                print(f"User selected: {selected_result['name']} ({selected_result['first_air_date']})")

                for file_data in files:
                    handled_files.append({
                        "file_path": file_data['file_path'],
                        "file_type": file_data['file_type'],
                        "season": file_data['season'],
                        "episode": file_data['episode'],
                        "details": selected_result,
                        "extras": file_data['extras']
                        })
            else:
                return None
    else:
        return [], []

    return handled_files, skipped_files

# ======================================================================
# ======================================================================
# ======================================================================

def pick_res(results, choice):
    selected_result = results[choice - 1]
    print(f"User selected: {selected_result['name']} ({selected_result['first_air_date']})")
    return selected_result

def select_for_group(files, file_type):
    prototype = files[0]
    results = prototype["series_details"]["results"]

    for idx, result in enumerate(results, start=1):
        print(f"{idx}. {result['name']} ({result['first_air_date']})")

    choice = None
    while choice is None:
        choice = ask_choice(len(results))

    return pick_res(results, choice)


def handle_episode_mult(episode_mult):
    handled_files = []

    folders, main_folders = group_by_folders(mult_res)

    for file_data in mult_res:
        file_type = file_data['file_type']
        print(f"Multiple {file_type} results found for: {file_data['file_path']}")

    first_folder_key = next(iter(folders))
    first_main_folder_key = next(iter(main_folders))

    action_choice = user_menu(mult_res, first_folder_key, first_main_folder_key)

    if action_choice == 1:
        for file_data in mult_res:
            file_type = file_data['file_type']
            results = file_data['data']['results']
            print(f"Multiple {file_type} results found for: {file_data['file_path']}")
            for idx, result in enumerate(results, start=1):
                print(f"{idx}. {result['name']} ({result['first_air_date']})")
            

            choice = None
            while choice is None:
                choice = ask_choice(len(results))

            selected_series = pick_res(results, choice)
            handled_files.append({
                "file_path": file_data['file_path'],
                "file_type": file_data['file_type'],
                "season": file_data['season'],
                "episode": file_data['episode'],
                "details": selected_series,
                "extras": file_data['extras']
            })

    elif action_choice == 2:
        for season_dir, files in folders.items():
            print(f"\nAttempting manual search for: {season_dir}")
            selected_series = select_for_group(files, file_type="episode")
            for file_data in files:
                handled_files.append({
                    "file_path": file_data['file_path'],
                    "file_type": file_data['file_type'],
                    "season": file_data['season'],
                    "episode": file_data['episode'],
                    "details": selected_series,
                    "extras": file_data['extras']
                })
    elif action_choice == 3:
        for series_dir, files in main_folders.items():
            print(f"\nAttempting manual search for: {series_dir}")
            selected_series = select_for_group(files, file_type="episode")
            for file_data in files:
                handled_files.append({
                    "file_path": file_data['file_path'],
                    "file_type": file_data['file_type'],
                    "season": file_data['season'],
                    "episode": file_data['episode'],
                    "details": selected_series,
                    "extras": file_data['extras']
                })
    elif action_choice == 4:
        return None

    return handled_files