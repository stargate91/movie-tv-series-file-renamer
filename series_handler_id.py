import os
from inputs import user_menu, ask_choice, get_data, ask_search
from outputs import display_res, pick_res
from outputs import manual_series_search_msg
from outputs import manual_search_dir_msg
from outputs import manual_search_main_dir_msg
from outputs import found_results_msg
from validators import not_empty_list

def search_series_tmdb(api_client, title, year):
    return api_client.get_from_tmdb_tv(title, year)

def handling_files(handled_files, file_data, selected_series):
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

def handle_no_series_res(no_res, api_client):
    handled_files = []

    not_empty_list(no_res, handled_files)    

    folders, main_folders = group_by_folders(no_res)

    for file_data in no_res:
        manual_series_search_msg(file_data)

    first_folder_key = next(iter(folders))
    first_main_folder_key = next(iter(main_folders))

    action_choice = user_menu(no_res, first_folder_key, first_main_folder_key)

    if action_choice == 1:
        for file_data in no_res:
            file_type = file_data['file_type']
            manual_series_search_msg(file_data)
            if ask_search():
                search_title, search_year = get_data(file_type="episode")
                data = search_series_tmdb(api_client, search_title, search_year)
                results = file_data['data']['results']
                found_results_msg()
                display_res(results, file_type)

                choice = None
                while choice is None:
                    choice = ask_choice(len(results), file_type)

                selected_series = pick_res(results, choice)
                handling_files(handled_files, file_data, selected_series)
            else:
                return None

    elif action_choice == 2:
        for season_dir, files in folders.items():
            manual_search_dir_msg(season_dir)
            if ask_search():
                search_title, search_year = get_data(file_type="episode")
                data = search_series_tmdb(api_client, search_title, search_year)
                results = data['results']
                found_results_msg()
                display_res(results, file_type="episode")

                choice = None
                while choice is None:
                    choice = ask_choice(len(results), file_type="episode")

                selected_series = pick_result(results, choice)

                for file_data in files:
                    handling_files(handled_files, file_data, selected_series)
            else:
                return None
    elif action_choice == 3:
        for series_dir, files in main_folders.items():
            manual_search_main_dir_msg(series_dir)
            if ask_search():
                search_title, search_year = get_data(file_type="episode")
                data = search_series_tmdb(api_client, search_title, search_year)
                results = data['results']
                found_results_msg()
                display_res(results, file_type="episode")

                choice = None
                while choice is None:
                    choice = ask_choice(len(results), file_type="episode")

                selected_series = pick_res(results, choice)

                for file_data in files:
                    handling_files(handled_files, file_data, selected_series)
            else:
                return None
    elif action_choice == 4:
        return None

    return handled_files

def handle_one_series_res(one_res):
    handled_files = []

    for file_data in one_res:
        file_path = file_data['file_path']
        file_type = file_data['file_type']
        season = file_data['season']
        episode = file_data['episode']
        extras = file_data['extras']

        raw = file_data['series_details']
        data = raw['results'][0]

        handling_files(handled_files, file_data, data)

    return handled_files

def select_for_group(files, file_type):
    prototype = files[0]
    results = prototype["series_details"]["results"]

    display_res(results, file_type)

    choice = None
    while choice is None:
        choice = ask_choice(len(results), file_type)

    return pick_res(results, choice)


def handle_mult_series_res(mult_res):
    handled_files = []

    not_empty_list(mult_res, handled_files)

    folders, main_folders = group_by_folders(mult_res)

    for file_data in mult_res:
        file_type = file_data['file_type']
        found_results_msg(file_data=file_data, file_type="episode")

    first_folder_key = next(iter(folders))
    first_main_folder_key = next(iter(main_folders))

    action_choice = user_menu(mult_res, first_folder_key, first_main_folder_key)

    if action_choice == 1:
        for file_data in mult_res:
            file_type = file_data['file_type']
            results = file_data['data']['results']
            found_results_msg(file_data=file_data, file_type="episode")
            display_res(results, file_type)

            choice = None
            while choice is None:
                choice = ask_choice(len(results), file_type)

            selected_series = pick_res(results, choice)
            handling_files(handled_files, file_data, selected_series)

    elif action_choice == 2:
        for season_dir, files in folders.items():
            manual_search_dir_msg(season_dir)
            selected_series = select_for_group(files, file_type="episode")
            for file_data in files:
                handling_files(handled_files, file_data, selected_series)
    elif action_choice == 3:
        for series_dir, files in main_folders.items():
            manual_search_main_dir_msg(series_dir)
            selected_series = select_for_group(files, file_type="episode")
            for file_data in files:
                handling_files(handled_files, file_data, selected_series)
    elif action_choice == 4:
        return None

    return handled_files
