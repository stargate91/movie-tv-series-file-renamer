import os

def user_menu_for_selection():
    menu_text = (
        "\nChoose how you want to apply the selected metadata:\n"
        "  1. Apply to a single file only\n"
        "  2. Apply to the entire folder\n"
        "  3. Apply to the main (parent) folder and all sub‑folders\n"
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

def ask_manual_search():
    return input("\nWould you like to search manually? (y/n): ").strip().lower() == 'y'

def get_manual_search_data():
    search_title = input("Enter series title: ").strip()
    search_year = input("Enter series year (or leave empty to skip): ").strip()
    return search_title, search_year if search_year else "Unknown"

def search_series_tmdb(api_client, title, year):
    return api_client.get_from_tmdb_tv(title, year)

def display_results(results):
    for idx, result in enumerate(results, start=1):
        first_air_date = result.get('first_air_date')
        name = result.get('name')
        print(f"{idx}. {name} ({first_air_date})")

def get_series_choice(max_choice):
    try:
        choice = int(input(f"Please select a series by number (1-{max_choice}): "))
        if 1 <= choice <= max_choice:
            return choice
        else:
            print(f"Please enter a number between 1 and {max_choice}.")
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

def pick_result(results, choice):
    selected_result = results[choice - 1]
    print(f"User selected: {selected_result['name']} ({selected_result['first_air_date']})")
    return selected_result

def handle_append(handled_files, file_data, selected_series):
    handled_files.append({
        "file_path": file_data['file_path'],
        "season": file_data['season'],
        "episode": file_data['episode'],
        "data": selected_series,
        "extras": file_data['extras']
    })

def group_by_folders(mult_res):
    folders = {}
    main_folders = {}

    for file_data in mult_res:
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

def handle_no_series_results(no_res, api_client):
    handled_files = []
    
    action_choice = user_menu_for_selection()

    if action_choice == 1:
        for file_data in no_res:
            print(f"\nAttempting manual search for: {file_data['file_path']}")

            if ask_manual_search():
                search_title, search_year = get_manual_search_data()
                data = search_series_tmdb(api_client, search_title, search_year)

                results = file_data['data']['results']

                display_results(results)

                choice = None
                while choice is None:
                    choice = get_series_choice(len(results))

                selected_series = pick_result(results, choice)
                handle_append(handled_files, file_data, selected_series)
            else:
                return None

    elif action_choice == 2:
        folders, _ = group_by_folders(no_res)
        for season_dir, files in folders.items():
            print(f"\nAttempting manual search for: {season_dir}")

            if ask_manual_search():
                search_title, search_year = get_manual_search_data()
                data = search_series_tmdb(api_client, search_title, search_year)
                results = data['results']
                print("Found results:")
                display_results(results)

                choice = None
                while choice is None:
                    choice = get_series_choice(len(results))

                selected_series = pick_result(results, choice)

                for file_data in files:
                    handle_append(handled_files, file_data, selected_series)
            else:
                return None
    elif action_choice == 3:
        _, main_folders = group_by_folders(no_res)
        for series_dir, files in main_folders.items():
            print(f"\nAttempting manual search for: {series_dir}")

            if ask_manual_search():
                search_title, search_year = get_manual_search_data()
                data = search_series_tmdb(api_client, search_title, search_year)
                results = data['results']
                print("Found results:")
                display_results(results)

                choice = None
                while choice is None:
                    choice = get_series_choice(len(results))

                selected_series = pick_result(results, choice)

                for file_data in files:
                    handle_append(handled_files, file_data, selected_series)
            else:
                return None
    elif action_choice == 4:
        return None

    return handled_files

def handle_one_series_result(one_res):
    handled_files = []

    for file_data in one_res:
        file_path = file_data.get('file_path')
        season = file_data.get('season')
        episode = file_data.get('episode')
        extras = file_data.get('extras')

        raw = file_data['data']
        data = raw['results'][0]

        handled_files.append({
            "file_path": file_path,
            "season": season,
            "episode": episode,
            "data": data,
            "extras": extras
        })

    return handled_files



def select_for_group(files):
    prototype = files[0]
    results = prototype["data"]["results"]

    display_results(results)

    choice = None
    while choice is None:
        choice = get_series_choice(len(results))

    return pick_result(results, choice)


def handle_multiple_series_results(mult_res):
    handled_files = []

    folders, main_folders = group_by_folders(mult_res)

    action_choice = user_menu_for_selection()

    if action_choice == 1:
        for file_data in mult_res:
            print(f"\nMultiple series results found for: {file_data['file_path']}")
            results = file_data['data']['results']

            display_results(results)

            choice = None
            while choice is None:
                choice = get_series_choice(len(results))

            selected_series = pick_result(results, choice)
            handle_append(handled_files, file_data, selected_series)

    elif action_choice == 2:
        for season_dir, files in folders.items():
            selected_series = select_for_group(files)
            for file_data in files:
                handle_append(handled_files, file_data, selected_series)
    elif action_choice == 3:
        for series_dir, files in main_folders.items():
            selected_series = select_for_group(files)
            for file_data in files:
                handle_append(handled_files, file_data, selected_series)
    elif action_choice == 4:
        return None

    return handled_files
