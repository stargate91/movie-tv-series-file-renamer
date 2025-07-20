import os

def normalize_season_episode(file_data):
    season = file_data.get('season_file') or file_data.get('season_folder') or 'unknown'
    episode = file_data.get('episode_file') or file_data.get('episode_folder') or 'unknown'

    if season == 'unknown':
        print(f"[WARNING] Missing season number for file data: {file_data}")
    if episode == 'unknown':
        print(f"[WARNING] Missing episode number for file data: {file_data}")

    return season, episode

def normalize_episodes(episodes, api_client, source=None):

    if not episodes:
        print(f"\n[INFO] There are no episodes to normalize in this pack: {source}.\n")
        return

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
                    'status': season_data.get('status', 'unknown'),
                    'last_air_date': last_air_date,
                    'last_air_year': last_air_date.split('-')[0]
                })
            else:
                season_details.update({
                    'status': season_data.get('status', 'unknown'),
                    'last_air_date': 'unknown',
                    'last_air_year': 'unknown'
                })
        else:
            season_details.update({
                'status': season_data.get('status', 'unknown'),
                'last_air_date': 'unknown',
                'last_air_year': 'unknown'                
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

def handle_cancellation(handled_episodes, skipped_episodes, remaining_source, mode, idx_or_processed=None):
    print("\n[INFO] Manual search cancelled by user.\n")

    if handled_episodes:
        print("\nMetadata stored for the following episodes:\n")
        for file in handled_episodes:
            print(f"[SAVED] {file['file_path']}")
    else:
        print("\nNo metadata was stored.")

    if skipped_episodes:
        print("\nThe following episodes were deferred for later:\n")
        for skip in skipped_episodes:
            print(f"[SKIPPED] {skip['file_path']}")

    remaining_episodes = []

    if mode == 1:
        remaining_episodes = remaining_source[idx_or_processed:]
    elif mode == 2:
        for dir_key, eps in remaining_source.items():
            if dir_key not in idx_or_processed:
                remaining_episodes.extend(eps)

    if remaining_episodes:
        print("\nThe following episodes were not processed:\n")
        for leftover in remaining_episodes:
            print(f"[INFO] {leftover['file_path']}")
    else:
        print("\n[INFO] All episodes have been processed.")

    return handled_episodes, skipped_episodes, remaining_episodes

# ======================================================================

def handle_episode_no(episode_no, api_client):
    print("\n=== EPISODES WITH NO SERIES MATCH ===\n")

    if not episode_no:
        print("\n[INFO] There are no episodes with no match. Continue with the next task.")
        return [], [], []

    for idx, episode in enumerate(episode_no, 1):
        print(f"{idx}. {episode['file_path']}")

    print("\nManual search required for these episodes.\n")

    folders, main_folders = group_by_folders(episode_no) 

    first_folder_key = next(iter(folders))
    first_main_folder_key = next(iter(main_folders))

    action_choice = user_menu(episode_no, first_folder_key, first_main_folder_key)

    skipped_episodes = []
    handled_episodes = []
    remaining_episodes = [] 

    if action_choice == 1:
        for idx, episode in enumerate(episode_no):
            print(f"\n Search for: {episode['file_path']}")
            title = input("Series title: ").strip()
            year = input("Series first air year (optional): ").strip() or 'unknown'

            while True:
                result = api_client.get_from_tmdb_tv(title, year)
                options = result.get('results') if result else []

                if not options:
                    print("No results found.")
                    print("Options:")
                    print("r: retry search")
                    print("s: skip")
                    print("c: cancel")
                    sel = input("Choice: ").strip().lower()
                    if sel == 'r':
                        title = input("Retry title: ").strip()
                        year = input("First air year (optional): ").strip() or 'unknown'
                        continue
                    elif sel == 's':
                        skipped_episodes.append(episode)
                        break
                    elif sel == 'c':
                        return handle_cancellation(
                            handled_episodes,
                            skipped_episodes,
                            episode_no,
                            mode=1,
                            idx_or_processed=idx
                        )
                    else:
                        print("Invalid input. Please enter r, s, or c.")

                print("Found results:")
                for i, opt in enumerate(options, 1):
                    print(f"{i}. {opt.get('name')} ({opt.get('first_air_date') or 'unknown'})")
                
                print("Select result by number, or:")
                print("r: retry search")
                print("s: skip")
                print("c: cancel")
                sel = input("Choice: ").strip().lower()
                valid_cmds = {'r', 's', 'c'}
                if sel.isdigit():
                    num = int(sel)
                    if 1 <= num <= len(options):
                        selected = options[num - 1]
                        handled_episodes.append({
                            'file_path': episode['file_path'],
                            'file_type': episode['file_type'],
                            'season_file': episode['season_file'],
                            'episode_file': episode['episode_file'],
                            'season_folder': episode['season_folder'],
                            'episode_folder': episode['episode_folder'],                                                        
                            'extras': episode['extras'],
                            'details': selected
                        })
                        break
                    else:
                        print("Invalid number.")
                elif sel in valid_cmds:
                    if sel == 'r':
                        title = input("Retry title: ").strip()
                        year = input("First air year (optional): ").strip() or 'unknown'
                        continue
                    elif sel == 's':
                        skipped_episodes.append(episode)
                        break
                    elif sel == 'c':
                        return handle_cancellation(
                            handled_episodes,
                            skipped_episodes,
                            episode_no,
                            mode=1,
                            idx_or_processed=idx
                        )
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(options)} or r, s, c.")

    elif action_choice == 2:
        processed_folders = []

        for season_dir, episodes in folders.items():

            print(f"\n Search for: {season_dir}")
            title = input("Series title: ").strip()
            year = input("Series first air year (optional): ").strip() or 'unknown'

            while True:
                result = api_client.get_from_tmdb_tv(title, year)
                options = result.get('results') if result else []

                if not options:
                    print("No results found.")
                    print("Options:")
                    print("r: retry search")
                    print("s: skip")
                    print("c: cancel")
                    sel = input("Choice: ").strip().lower()
                    if sel == 'r':
                        title = input("Retry title: ").strip()
                        year = input("First air year (optional): ").strip() or 'unknown'
                        continue
                    elif sel == 's':
                        skipped_episodes.extend(episodes)
                        break
                    elif sel == 'c':
                        return handle_cancellation(
                            handled_episodes,
                            skipped_episodes,
                            folders,
                            mode=2,
                            idx_or_processed=processed_folders
                        )
                    else:
                        print("Invalid input. Please enter r, s, or c.")

                print("Found results:")
                for i, opt in enumerate(options, 1):
                    print(f"{i}. {opt.get('name')} ({opt.get('first_air_date') or 'unknown'})")
                
                print("Select result by number, or:")
                print("r: retry search")
                print("s: skip")
                print("c: cancel")
                sel = input("Choice: ").strip().lower()
                valid_cmds = {'r', 's', 'c'}
                if sel.isdigit():
                    num = int(sel)
                    if 1 <= num <= len(options):
                        selected = options[num - 1]
                        for episode in episodes:
                            handled_episodes.append({
                            'file_path': episode['file_path'],
                            'file_type': episode['file_type'],
                            'season_file': episode['season_file'],
                            'episode_file': episode['episode_file'],
                            'season_folder': episode['season_folder'],
                            'episode_folder': episode['episode_folder'],                                                        
                            'extras': episode['extras'],
                            'details': selected
                            })
                        processed_folders.append(season_dir)
                        break
                    else:
                        print("Invalid number.")
                elif sel in valid_cmds:
                    if sel == 'r':
                        title = input("Retry title: ").strip()
                        year = input("First air year (optional): ").strip() or 'unknown'
                        continue
                    elif sel == 's':
                        skipped_episodes.extend(episodes)
                        break
                    elif sel == 'c':
                        return handle_cancellation(
                            handled_episodes,
                            skipped_episodes,
                            folders,
                            mode=2,
                            idx_or_processed=processed_folders
                        )
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(options)} or r, s, c.")

    elif action_choice == 3:
        processed_folders = []

        for series_dir, episodes in main_folders.items():

            print(f"\n Search for: {series_dir}")
            title = input("Series title: ").strip()
            year = input("Series first air year (optional): ").strip() or 'unknown'

            while True:
                result = api_client.get_from_tmdb_tv(title, year)
                options = result.get('results') if result else []

                if not options:
                    print("No results found.")
                    print("Options:")
                    print("r: retry search")
                    print("s: skip")
                    print("c: cancel")
                    sel = input("Choice: ").strip().lower()
                    if sel == 'r':
                        title = input("Retry title: ").strip()
                        year = input("First air year (optional): ").strip() or 'unknown'
                        continue
                    elif sel == 's':
                        skipped_episodes.extend(episodes)
                        break
                    elif sel == 'c':
                        return handle_cancellation(
                            handled_episodes,
                            skipped_episodes,
                            main_folders,
                            mode=2,
                            idx_or_processed=processed_folders
                        )
                    else:
                        print("Invalid input. Please enter r, s, or c.")

                print("Found results:")
                for i, opt in enumerate(options, 1):
                    print(f"{i}. {opt.get('name')} ({opt.get('first_air_date') or 'unknown'})")
                
                print("Select result by number, or:")
                print("r: retry search")
                print("s: skip")
                print("c: cancel")
                sel = input("Choice: ").strip().lower()
                valid_cmds = {'r', 's', 'c'}
                if sel.isdigit():
                    num = int(sel)
                    if 1 <= num <= len(options):
                        selected = options[num - 1]
                        for episode in episodes:
                            handled_episodes.append({
                            'file_path': episode['file_path'],
                            'file_type': episode['file_type'],
                            'season_file': episode['season_file'],
                            'episode_file': episode['episode_file'],
                            'season_folder': episode['season_folder'],
                            'episode_folder': episode['episode_folder'],                                                        
                            'extras': episode['extras'],
                            'details': selected
                            })
                        processed_folders.append(series_dir)
                        break
                    else:
                        print("Invalid number.")
                elif sel in valid_cmds:
                    if sel == 'r':
                        title = input("Retry title: ").strip()
                        year = input("First air year (optional): ").strip() or 'unknown'
                        continue
                    elif sel == 's':
                        skipped_episodes.extend(episodes)
                        break
                    elif sel == 'c':
                        return handle_cancellation(
                            handled_episodes,
                            skipped_episodes,
                            main_folders,
                            mode=2,
                            idx_or_processed=processed_folders
                        )
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(options)} or r, s, c.")

    else:
        print("\n[INFO] Manual search cancelled by user.")
        return [], [], []

    return handled_episodes, skipped_episodes, remaining_episodes

# ======================================================================
# ======================================================================
# ======================================================================

def handle_episode_mult(episode_mult, api_client):
    print("\n=== EPISODES WITH MULTIPLE SERIES MATCHES ===\n")

    if not episode_mult:
        print("\n[INFO] There are no episodes with multiple matches. Continue with the next task.")
        return [], [], []

    for idx, episode in enumerate(episode_mult, 1):
        print(f"{idx}. {episode['file_path']}")

    print("\nManual selection required for these episodes.\n")

    folders, main_folders = group_by_folders(episode_mult) 

    first_folder_key = next(iter(folders))
    first_main_folder_key = next(iter(main_folders))

    action_choice = user_menu(episode_mult, first_folder_key, first_main_folder_key)

    skipped_episodes = []
    handled_episodes = []
    remaining_episodes = [] 

    if action_choice == 1:

        for idx, episode in enumerate(episode_mult):
            results = episode['details']['results']
            print(f"\n Choose a result or an action for this episode: {episode['file_path']}")

            for idx, res in enumerate(results, start=1):
                print(f"{idx}. {res['name']} ({res['first_air_date'] or 'unknown'})")

            print("Select result by number, or:")
            print("r: retry search")
            print("s: skip")
            print("c: cancel")

            while True:
                sel = input("Choice: ").strip().lower()
                valid_cmds = {'r', 's', 'c'}
                if sel.isdigit():
                    num = int(sel)
                    if 1 <= num <= len(results):
                        selected = results[num - 1]
                        handled_episodes.append({
                            'file_path': episode['file_path'],
                            'file_type': episode['file_type'],
                            'season_file': episode['season_file'],
                            'episode_file': episode['episode_file'],
                            'season_folder': episode['season_folder'],
                            'episode_folder': episode['episode_folder'],                                                        
                            'extras': episode['extras'],
                            'details': selected
                        })
                        break
                    else:
                        print("Invalid number.")
                elif sel in valid_cmds:
                    if sel == 'r':
                        title = input("Retry title: ").strip()
                        year = input("First air year (optional): ").strip() or 'unknown'
                        result = api_client.get_from_tmdb_tv(title, year)
                        results = result.get('results') if result else []
                        if results:
                            print("Found results:")
                            for i, res in enumerate(results, 1):
                                print(f"{i}. {res.get('name')} ({res.get('first_air_date') or 'unknown'})")
                            else:
                                print("No results.")
                    elif sel == 's':
                        skipped_episodes.append(episode)
                        break
                    elif sel == 'c':
                        return handle_cancellation(
                            handled_episodes,
                            skipped_episodes,
                            episode_no,
                            mode=1,
                            idx_or_processed=idx
                        )
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(results)} or r, s, c.")              

    elif action_choice == 2:
        processed_folders = []

        for season_dir, episodes in folders.items():
            prototype = episodes[0]
            results = prototype['details']['results']

            print(f"\n Choose a result or an action for this folder: {season_dir}")

            for idx, res in enumerate(results, start=1):
                print(f"{idx}. {res['name']} ({res['first_air_date'] or 'unknown'})")

            print("Select result by number, or:")
            print("r: retry search")
            print("s: skip")
            print("c: cancel")

            while True:
                sel = input("Choice: ").strip().lower()
                valid_cmds = {'r', 's', 'c'}
                if sel.isdigit():
                    num = int(sel)
                    if 1 <= num <= len(results):
                        selected = results[num - 1]
                        for episode in episodes:
                            handled_episodes.append({
                            'file_path': episode['file_path'],
                            'file_type': episode['file_type'],
                            'season_file': episode['season_file'],
                            'episode_file': episode['episode_file'],
                            'season_folder': episode['season_folder'],
                            'episode_folder': episode['episode_folder'],                                                        
                            'extras': episode['extras'],
                            'details': selected
                            })
                        processed_folders.append(season_dir)
                        break
                    else:
                        print("Invalid number.")
                elif sel in valid_cmds:
                    if sel == 'r':
                        title = input("Retry title: ").strip()
                        year = input("First air year (optional): ").strip() or 'unknown'
                        result = api_client.get_from_tmdb_tv(title, year)
                        results = result.get('results') if result else []
                        if results:
                            print("Found results:")
                            for i, res in enumerate(results, 1):
                                print(f"{i}. {res.get('name')} ({res.get('first_air_date') or 'unknown'})")
                            else:
                                print("No results.")
                    elif sel == 's':
                        skipped_episodes.append(episodes)
                        break
                    elif sel == 'c':
                        return handle_cancellation(
                            handled_episodes,
                            skipped_episodes,
                            episode_mult,
                            mode=2,
                            idx_or_processed=processed_folders
                        )
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(results)} or r, s, c.")

    elif action_choice == 3:
        processed_folders = []

        for series_dir, episodes in main_folders.items():
            prototype = episodes[0]
            results = prototype['details']['results']

            print(f"\n Choose a result or an action for this folder: {series_dir}")

            for idx, res in enumerate(results, start=1):
                print(f"{idx}. {res['name']} ({res['first_air_date'] or 'unknown'})")

            print("Select result by number, or:")
            print("r: retry search")
            print("s: skip")
            print("c: cancel")

            while True:
                sel = input("Choice: ").strip().lower()
                valid_cmds = {'r', 's', 'c'}
                if sel.isdigit():
                    num = int(sel)
                    if 1 <= num <= len(results):
                        selected = results[num - 1]
                        for episode in episodes:
                            handled_episodes.append({
                            'file_path': episode['file_path'],
                            'file_type': episode['file_type'],
                            'season_file': episode['season_file'],
                            'episode_file': episode['episode_file'],
                            'season_folder': episode['season_folder'],
                            'episode_folder': episode['episode_folder'],                                                        
                            'extras': episode['extras'],
                            'details': selected
                            })
                        processed_folders.append(series_dir)
                        break
                    else:
                        print("Invalid number.")
                elif sel in valid_cmds:
                    if sel == 'r':
                        title = input("Retry title: ").strip()
                        year = input("First air year (optional): ").strip() or 'unknown'
                        result = api_client.get_from_tmdb_tv(title, year)
                        results = result.get('results') if result else []
                        if results:
                            print("Found results:")
                            for i, res in enumerate(results, 1):
                                print(f"{i}. {res.get('name')} ({res.get('first_air_date') or 'unknown'})")
                            else:
                                print("No results.")
                    elif sel == 's':
                        skipped_episodes.append(episodes)
                        break
                    elif sel == 'c':
                        return handle_cancellation(
                            handled_episodes,
                            skipped_episodes,
                            episode_mult,
                            mode=2,
                            idx_or_processed=processed_folders
                        )
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(results)} or r, s, c.")
    else:
        print("\n[INFO] Manual selection cancelled by user.")
        return [], [], []

    return handled_episodes, skipped_episodes, remaining_episodes