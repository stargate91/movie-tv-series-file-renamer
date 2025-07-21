from ui_ux import print_cancellation_summary, user_menu
import os

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
                        return print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=episode_no,
                            mode=1,
                            idx_or_processed=idx,
                            content="series",
                            action="search"
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
                        return print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=episode_no,
                            mode=1,
                            idx_or_processed=idx,
                            content="series",
                            action="search"
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
                        return print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=folders,
                            mode=2,
                            idx_or_processed=processed_folders,
                            content="series",
                            action="search"
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
                        return print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=folders,
                            mode=2,
                            idx_or_processed=processed_folders,
                            content="series",
                            action="search"
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
                        return print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=main_folders,
                            mode=2,
                            idx_or_processed=processed_folders,
                            content="series",
                            action="search"
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
                        return print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=main_folders,
                            mode=2,
                            idx_or_processed=processed_folders,
                            content="series",
                            action="search"
                        )
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(options)} or r, s, c.")

    else:
        return print_cancellation_summary(action="search")

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
                        return print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=episode_mult,
                            mode=1,
                            idx_or_processed=idx,
                            content="series",
                            action="selection"
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
                        skipped_episodes.extend(episodes)
                        break
                    elif sel == 'c':
                        return print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=folders,
                            mode=2,
                            idx_or_processed=processed_folders,
                            content="series",
                            action="selection"
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
                        skipped_episodes.extend(episodes)
                        break
                    elif sel == 'c':
                        return print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=main_folders,
                            mode=2,
                            idx_or_processed=processed_folders,
                            content="series",
                            action="selection"
                        )
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(results)} or r, s, c.")
    else:
        return print_cancellation_summary(action="selection")

    return handled_episodes, skipped_episodes, remaining_episodes
