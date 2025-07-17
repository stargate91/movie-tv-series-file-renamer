from inputs import ask_manual_search, get_manual_movie_search_data, ask_for_movie_choice
from outputs import api_arg_error_msg, found_omdb_result_message, no_manual_results_found, invalid_choice_message, found_results_message
from outputs import multiple_movie_results_message, attempting_manual_search_message, skiping_manual_search_message
from outputs import display_results, selected_result_message

def search_movie_tmdb(api_client, title, year):
    return api_client.get_from_tmdb_movie(title, year)

def search_movie_omdb(api_client, title, year):
    return api_client.get_from_omdb(title, year)

def process_search_results(api_source, data, file_data):
    if api_source == "omdb":
        if data.get("Response") == "True":
            found_omdb_result_message(data)
            return {
                "file_path": file_data['file_path'],
                "file_type": file_data['file_type'],
                "movie_details": data,
                "extras": extras
                }
        else:
            no_manual_results_found()
            return None
    elif api_source == "tmdb":
        if data.get("total_results") > 0:
            results = data['results']
            found_results_message()
            display_results(results)

            choice = ask_for_movie_choice(len(results))

            if choice:
                selected_result = results[choice - 1]
                selected_result_message(selected_result)
                return {
                    "file_path": file_data['file_path'],
                    "file_type": file_data['file_type'],
                    "movie_details": selected_result,
                    "extras": file_data['extras']
                    }
            else:
                invalid_choice_message()
                return None
        else:
            no_manual_results_found()
            return None

def handle_no_movie_results(no_res, api_client, api_source):
    handled_files = []

    for file_data in no_res:
        file_type = file_data.get('file_type')
        extras = file_data.get('extras')
        attempting_manual_search_message(file_data)
        if ask_manual_search():
            search_title, search_year = get_manual_movie_search_data()

            if api_source == "omdb":
                data = search_movie_omdb(api_client, search_title, search_year)
            elif api_source == "tmdb":
                data = search_movie_tmdb(api_client, search_title, search_year)
            else:
                incorrect_api_arguments_message()
                continue

            if data:
                handled_files.append(process_search_results(api_source, data, file_data))

        else:
            skiping_manual_search_message(file_data)
    return handled_files

def handle_multiple_movie_results(mult_res):
    handled_files = []

    for file_data in mult_res:
        file_type = file_data.get('file_type')
        extras = file_data.get('extras')
        multiple_movie_results_message(file_data)
        results = file_data['movie_details']['results']
        
        display_results(results)

        choice = ask_for_movie_choice(len(results))
        
        if choice:
            selected_result = results[choice - 1]
            selected_result_message(selected_result)
            
            handled_files.append({
                "file_path": file_data['file_path'],
                "file_type": file_data['file_type'],
                "movie_details": selected_result,
                "extras": extras
                })
        else:
            invalid_choice_message()
    
    return handled_files
