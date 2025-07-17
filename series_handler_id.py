import os
from inputs import user_menu_for_selection, get_series_choice, get_manual_series_search_data, ask_manual_search
from outputs import display_series_results, pick_result
from outputs import manual_series_search_message, attempting_manual_search_message
from outputs import attempting_manual_search_message_for_dir
from outputs import found_results_message, attempting_manual_search_message_for_main_dir
from outputs import multiple_series_results_message

def search_series_tmdb(api_client, title, year):
    return api_client.get_from_tmdb_tv(title, year)

def handle_append(handled_files, file_data, selected_series):
    handled_files.append({
        "file_path": file_data['file_path'],
        "file_type": file_data['file_type'],
        "season": file_data['season'],
        "episode": file_data['episode'],
        "series_details": selected_series,
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

    if not no_res:
        print("No results to handle.")
        return handled_files    

    folders, main_folders = group_by_folders(no_res)

    for file_data in no_res:
        manual_series_search_message(file_data)

    first_folder_key = next(iter(folders))
    first_main_folder_key = next(iter(main_folders))

    action_choice = user_menu_for_selection(no_res, first_folder_key, first_main_folder_key)

    if action_choice == 1:
        for file_data in no_res:
            attempting_manual_search_message(file_data)
            if ask_manual_search():
                search_title, search_year = get_manual_series_search_data()
                data = search_series_tmdb(api_client, search_title, search_year)

                results = file_data['data']['results']

                display_series_results(results)

                choice = None
                while choice is None:
                    choice = get_series_choice(len(results))

                selected_series = pick_result(results, choice)
                handle_append(handled_files, file_data, selected_series)
            else:
                return None

    elif action_choice == 2:
        for season_dir, files in folders.items():
            attempting_manual_search_message_for_dir(season_dir)
            if ask_manual_search():
                search_title, search_year = get_manual_series_search_data()
                data = search_series_tmdb(api_client, search_title, search_year)
                results = data['results']
                found_results_message()
                display_series_results(results)

                choice = None
                while choice is None:
                    choice = get_series_choice(len(results))

                selected_series = pick_result(results, choice)

                for file_data in files:
                    handle_append(handled_files, file_data, selected_series)
            else:
                return None
    elif action_choice == 3:
        for series_dir, files in main_folders.items():
            attempting_manual_search_message_for_main_dir(series_dir)
            if ask_manual_search():
                search_title, search_year = get_manual_series_search_data()
                data = search_series_tmdb(api_client, search_title, search_year)
                results = data['results']
                found_results_message()
                display_series_results(results)

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
        file_type = file_data.get('file_type')
        season = file_data.get('season')
        episode = file_data.get('episode')
        extras = file_data.get('extras')

        raw = file_data['series_details']
        data = raw['results'][0]

        handled_files.append({
            "file_path": file_path,
            "file_type": file_type,
            "season": season,
            "episode": episode,
            "series_details": data,
            "extras": extras
        })

    return handled_files

def select_for_group(files):
    prototype = files[0]
    results = prototype["series_details"]["results"]

    display_series_results(results)

    choice = None
    while choice is None:
        choice = get_series_choice(len(results))

    return pick_result(results, choice)


def handle_multiple_series_results(mult_res):
    handled_files = []

    if not mult_res:
        print("No results to handle.")
        return handled_files

    folders, main_folders = group_by_folders(mult_res)

    for file_data in mult_res:
        multiple_series_results_message(file_data)

    first_folder_key = next(iter(folders))
    first_main_folder_key = next(iter(main_folders))

    action_choice = user_menu_for_selection(mult_res, first_folder_key, first_main_folder_key)

    if action_choice == 1:
        for file_data in mult_res:
            multiple_series_results_message(file_data)
            results = file_data['data']['results']

            display_series_results(results)

            choice = None
            while choice is None:
                choice = get_series_choice(len(results))

            selected_series = pick_result(results, choice)
            handle_append(handled_files, file_data, selected_series)

    elif action_choice == 2:
        for season_dir, files in folders.items():
            attempting_manual_search_message_for_dir(season_dir)
            selected_series = select_for_group(files)
            for file_data in files:
                handle_append(handled_files, file_data, selected_series)
    elif action_choice == 3:
        for series_dir, files in main_folders.items():
            attempting_manual_search_message_for_main_dir(series_dir)
            selected_series = select_for_group(files)
            for file_data in files:
                handle_append(handled_files, file_data, selected_series)
    elif action_choice == 4:
        return None

    return handled_files
