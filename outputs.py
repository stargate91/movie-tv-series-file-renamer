import os

# ----- File operations messages -----

def proc_file_msg(file_path):
    print(f"Processing file: {file_path}")

def res_error_msg(file_path, e):
    print(f"[ERROR] Error getting resolution for {file_path}: {e}")

def rename_success_msg(file_path, new_filename):
    rel_path = os.path.relpath(file_path)
    print(f"Old name: {rel_path} → New name: {new_filename}")

def dry_rename_msg(file_path, new_filename):
    rel_path = os.path.relpath(file_path)
    print(f"[DRY RUN] Old name: {rel_path} → New name: {new_filename}")

# ----- Metadata handling messages -----

def unknown_type_msg(item, file_type):
    print(f"[ERROR] Unknown file type for {item}: {file_type}")

def sorted_success_msg(file, file_type):
    rel_path = os.path.relpath(file)
    print(f"{rel_path} added to {file_type} files")

def api_arg_error_msg():
    print("[ERROR] Unsupported API source for manual search")

def result_message(file_path, Response=None, total_results=None, data=None):
    rel_path = os.path.relpath(file_path)

    if Response == "False" or total_results == 0:
        print(f"No results found for {rel_path}")

    elif Response == "True" or total_results == 1:
        print(f"One result found for {rel_path}: {data}")
    
    elif total_results > 1:
        print(f"Multiple results found for {rel_path}: {data}")

    else:
        print(f"No data found for {rel_path}")

# ----- Movie metadata handling messages -----

def found_omdb_result_message(data):
    print(f"Found result: {data['Title']} ({data['Year']})")

def no_manual_results_found():
    print(f"No manual results found.")

def invalid_choice_message():
    print("Invalid choice. No movie selected.")

def found_results_message():
    print("Found results:")

def multiple_movie_results_message(file_data):
    print(f"\nMultiple movie results found for: {file_data['file_path']}")

def attempting_manual_search_message(file_data):
    print(f"\nAttempting manual search for: {file_data['file_path']}")

def skiping_manual_search_message(file_data):
    print(f"Skipping manual search for {file_data['file_path']}.")

def display_results(results):
    for idx, result in enumerate(results, start=1):
        print(f"{idx}. {result['title']} ({result['release_date']})")

def selected_result_message(selected_result):
    print(f"User selected: {selected_result['title']} ({selected_result['release_date']})")

# ----- Series metadata handling messages -----

def display_series_results(results):
    for idx, result in enumerate(results, start=1):
        first_air_date = result.get('first_air_date')
        name = result.get('name')
        print(f"{idx}. {name} ({first_air_date})")

def pick_result(results, choice):
    selected_result = results[choice - 1]
    print(f"User selected: {selected_result['name']} ({selected_result['first_air_date']})")
    return selected_result

def manual_series_search_message(file_data):
    print(f"Manual series search required for {file_data['file_path']}")

def attempting_manual_search_message_for_dir(season_dir):
    print(f"\nAttempting manual search for: {season_dir}")

def attempting_manual_search_message_for_main_dir(series_dir):
    print(f"\nAttempting manual search for: {series_dir}")

def multiple_series_results_message(file_data):
    print(f"Multiple series results found for: {file_data['file_path']}")

# ----- Episode metadata handling messages -----

def no_episode_found(file_path):
    print(f"No episode found for {file_path}")

# ----- Main messages -----

def done_message(unknown):
    print("\n Done.")
    print("\n Unexpected files:")
    for file_data in unknown:
        print(f"\n [MANUAL RENAMING REQ] {file_data['file_path']}")
