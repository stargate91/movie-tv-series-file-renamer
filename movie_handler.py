from inputs import ask_search, get_data, ask_choice
from outputs import api_arg_error_msg, found_omdb_msg, no_manual_results_msg
from outputs import found_results_msg, manual_search_msg, skip_manual_search_msg
from outputs import display_res, selected_res_msg

def search_tmdb(api_client, title, year):
    return api_client.get_from_tmdb_movie(title, year)

def search_omdb(api_client, title, year):
    return api_client.get_from_omdb(title, year)

def handling_files(handled_files, file_data, data):
    handled_files.append({
        "file_path": file_data['file_path'],
        "file_type": file_data['file_type'],
        "movie_details": data,
        "extras": file_data['extras']
    })

def choice(results, file_type, handled_files, file_data):
    choice = None
    while choice is None:
        choice = ask_choice(len(results), file_type)

    data = results[choice - 1]
    selected_res_msg(data)
    handling_files(handled_files, file_data, data)

def handle_no_movie_res(no_res, api_client, api_source):
    handled_files = []

    for file_data in no_res:
        file_type = file_data['file_type']

        manual_search_msg(file_data)
        
        if ask_search():
            search_title, search_year = get_data(file_type)

            if api_source == "omdb":
                data = search_omdb(api_client, search_title, search_year)
            elif api_source == "tmdb":
                data = search_tmdb(api_client, search_title, search_year)

            if data:
                if api_source == "omdb":
                    if data.get("Response") == "True":
                        found_omdb_msg(data)
                        handling_files(handled_files, file_data, data)
                    else:
                        no_manual_results_msg()
                
                elif api_source == "tmdb":
                    if data.get("total_results") > 0:
                        results = data['results']
                        found_results_msg()
                        display_res(results, file_type)

                        choice(results, file_type, handled_files, file_data)
                    else:
                        no_manual_results_msg()
            else:
                no_manual_results_msg()
        else:
            skip_manual_search_msg(file_data)
    
    return handled_files


def handle_mult_movie_res(mult_res):
    handled_files = []

    for file_data in mult_res:
        file_type = file_data['file_type']
        results = file_data['movie_details']['results']

        found_results_msg(file_data=file_data, file_type="movie")        
        display_res(results, file_type)

        choice(results, file_type, handled_files, file_data)
    
    return handled_files

def extract_movie_details(raw):
    if 'results' in raw and isinstance(raw['results'], list):
        return raw['results'][0]
    elif 'Title' in raw:
        return raw
    else:
        raise ValueError("Unknown movie details format")

def handle_one_movie_res(one_res):
    handled_files = []

    for file_data in one_res:
        file_path = file_data['file_path']
        file_type = file_data['file_type']
        extras = file_data['extras']
        raw = file_data.get('movie_details')

        movie_details = extract_movie_details(raw)

        handling_files(handled_files, file_data, movie_details)

    return handled_files
